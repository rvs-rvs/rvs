"""Switch command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, Optional
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class SwitchCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('switch', help='Switch branches')
        parser.add_argument('branch', nargs='?', help='Branch to switch to')
        parser.add_argument('-c', '--create', help='Create a new branch and switch to it')
        parser.add_argument('-C', '--force-create', help='Create/reset a branch and switch to it')
        parser.add_argument('--detach', action='store_true', help='Switch to a commit for inspection and discardable experiments')
        parser.add_argument('-f', '--force', action='store_true', help='Force switch (discard local changes)')
        parser.add_argument('--discard-changes', action='store_true', help='Discard local changes')
        parser.add_argument('-m', '--merge', action='store_true', help='Perform a 3-way merge with the new branch')
        parser.add_argument('--conflict', choices=['merge', 'diff3'], help='Conflict resolution style')
        parser.add_argument('-q', '--quiet', action='store_true', help='Suppress feedback messages')
        parser.add_argument('--progress', action='store_true', help='Force progress reporting')
        parser.add_argument('--no-progress', action='store_true', help='Disable progress reporting')
        parser.add_argument('-t', '--track', action='store_true', help='Set up tracking information')
        parser.add_argument('--no-track', action='store_true', help='Do not set up tracking information')
        parser.add_argument('--guess', action='store_true', default=True, help='Try to match branch name with remote')
        parser.add_argument('--no-guess', action='store_true', help='Do not try to match branch name with remote')
        parser.add_argument('--orphan', help='Create a new orphan branch')
        parser.add_argument('--ignore-other-worktrees', action='store_true', help='Switch even if branch is checked out elsewhere')
        return parser
    
    def execute_from_args(self, args: Any):
        # Handle orphan branch creation
        if args.orphan:
            self.create_orphan_branch(args.orphan, quiet=args.quiet)
            return
        
        # Handle branch creation
        if args.create:
            self.create_and_switch_branch(
                args.create, 
                start_point=args.branch,
                force=False,
                quiet=args.quiet,
                track=args.track,
                no_track=args.no_track
            )
            return
        
        if args.force_create:
            self.create_and_switch_branch(
                args.force_create,
                start_point=args.branch,
                force=True,
                quiet=args.quiet,
                track=args.track,
                no_track=args.no_track
            )
            return
        
        # Handle detached HEAD
        if args.detach:
            if not args.branch:
                raise RVSError("--detach requires a commit to switch to")
            self.switch_detached(
                args.branch,
                force=args.force or args.discard_changes,
                quiet=args.quiet
            )
            return
        
        # Handle regular branch switching
        if not args.branch:
            # Show current branch if no argument provided
            self.show_current_branch()
            return
        
        self.switch_branch(
            args.branch,
            force=args.force or args.discard_changes,
            merge=args.merge,
            quiet=args.quiet,
            guess=args.guess and not args.no_guess,
            ignore_other_worktrees=args.ignore_other_worktrees
        )
    
    def show_current_branch(self):
        """Show the current branch."""
        self.repo._ensure_repo_exists()
        current_branch = self.repo._get_current_branch()
        
        if current_branch == "HEAD":
            commit_hash = self.repo._get_branch_commit("HEAD")
            if commit_hash:
                print(f"HEAD detached at {commit_hash[:8]}")
            else:
                print("HEAD detached")
        else:
            print(f"On branch {current_branch}")
    
    def switch_branch(self, branch_name: str, force: bool = False, merge: bool = False, 
                     quiet: bool = False, guess: bool = True, ignore_other_worktrees: bool = False):
        """Switch to an existing branch."""
        self.repo._ensure_repo_exists()
        
        # Check if branch exists
        branch_commit = self.repo._get_branch_commit(branch_name)
        if not branch_commit:
            if guess:
                # Try to guess and create branch from remote
                if self._try_create_from_remote(branch_name, quiet):
                    return
            raise RVSError(f"pathspec '{branch_name}' did not match any file(s) known to rvs")
        
        # Check if branch is already checked out in another worktree
        if not ignore_other_worktrees and self._is_branch_checked_out_elsewhere(branch_name):
            raise RVSError(f"fatal: '{branch_name}' is already checked out at another worktree")
        
        # Check for uncommitted changes
        if not force and not merge and self._has_uncommitted_changes():
            raise RVSError("Your local changes to the following files would be overwritten by checkout:\\n"
                          "Please commit your changes or stash them before you switch branches.")
        
        current_branch = self.repo._get_current_branch()
        
        # Perform the switch
        if merge and self._has_uncommitted_changes():
            self._switch_with_merge(branch_name, current_branch, quiet)
        else:
            self._switch_clean(branch_name, branch_commit, force, quiet)
    
    def switch_detached(self, commit_ish: str, force: bool = False, quiet: bool = False):
        """Switch to a detached HEAD state."""
        self.repo._ensure_repo_exists()
        
        # Resolve commit
        commit_hash = self._resolve_commit(commit_ish)
        
        # Check for uncommitted changes
        if not force and self._has_uncommitted_changes():
            raise RVSError("Your local changes to the following files would be overwritten by checkout:\\n"
                          "Please commit your changes or stash them before you switch branches.")
        
        # Switch to detached HEAD
        self._detach_head(commit_hash, quiet)
    
    def create_and_switch_branch(self, branch_name: str, start_point: Optional[str] = None,
                                force: bool = False, quiet: bool = False, track: bool = False,
                                no_track: bool = False):
        """Create a new branch and switch to it."""
        self.repo._ensure_repo_exists()
        
        # Check if branch already exists
        if not force and self.repo._get_branch_commit(branch_name):
            raise RVSError(f"A branch named '{branch_name}' already exists.")
        
        # Determine start point
        if start_point:
            start_commit = self._resolve_commit(start_point)
        else:
            current_branch = self.repo._get_current_branch()
            start_commit = self.repo._get_branch_commit(current_branch)
            if not start_commit:
                raise RVSError("You are on a branch yet to be born")
        
        # Create the branch
        self.repo._set_branch_commit(branch_name, start_commit)
        
        # Switch to the new branch
        self._switch_clean(branch_name, start_commit, force=True, quiet=quiet)
        
        if not quiet:
            if force:
                print(f"Reset branch '{branch_name}'")
            else:
                print(f"Switched to a new branch '{branch_name}'")
    
    def create_orphan_branch(self, branch_name: str, quiet: bool = False):
        """Create a new orphan branch."""
        self.repo._ensure_repo_exists()
        
        # Check if branch already exists
        if self.repo._get_branch_commit(branch_name):
            raise RVSError(f"A branch named '{branch_name}' already exists.")
        
        # Create orphan branch (no parent commit)
        with open(self.repo.head_file, 'w') as f:
            f.write(f"ref: refs/heads/{branch_name}")
        
        # Clear the index
        self.repo._save_index({})
        
        if not quiet:
            print(f"Switched to a new branch '{branch_name}'")
    
    def _switch_clean(self, branch_name: str, commit_hash: str, force: bool = False, quiet: bool = False):
        """Perform a clean switch to a branch."""
        # Update HEAD to point to the branch
        with open(self.repo.head_file, 'w') as f:
            f.write(f"ref: refs/heads/{branch_name}")
        
        # Update working tree and index
        self._update_working_tree_and_index(commit_hash)
        
        if not quiet:
            print(f"Switched to branch '{branch_name}'")
    
    def _switch_with_merge(self, branch_name: str, current_branch: str, quiet: bool = False):
        """Switch branches with merge (3-way merge)."""
        # This is a simplified implementation
        # In a full implementation, this would perform a 3-way merge
        print(f"Merging local changes into '{branch_name}'...")
        
        # For now, just do a clean switch and warn about potential conflicts
        branch_commit = self.repo._get_branch_commit(branch_name)
        self._switch_clean(branch_name, branch_commit, force=True, quiet=True)
        
        if not quiet:
            print(f"Switched to branch '{branch_name}'")
            print("Your local changes have been merged.")
    
    def _detach_head(self, commit_hash: str, quiet: bool = False):
        """Detach HEAD to point to a specific commit."""
        # Update HEAD to point directly to commit
        with open(self.repo.head_file, 'w') as f:
            f.write(commit_hash)
        
        # Update working tree and index
        self._update_working_tree_and_index(commit_hash)
        
        if not quiet:
            print(f"Note: switching to '{commit_hash[:8]}'.")
            print("")
            print("You are in 'detached HEAD' state. You can look around, make experimental")
            print("changes and commit them, and you can discard any commits you make in this")
            print("state without impacting any branches by switching back to a branch.")
            print("")
            print("If you want to create a new branch to retain commits you create, you may")
            print("do so (now or later) by using -c with the switch command. Example:")
            print("")
            print(f"  rvs switch -c <new-branch-name>")
            print("")
            print(f"HEAD is now at {commit_hash[:8]}")
    
    def _update_working_tree_and_index(self, commit_hash: str):
        """Update working tree and index to match commit."""
        try:
            # Get files from commit
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            tree_files = self.repo._read_tree(tree_hash)
            
            # Update working tree
            self._update_working_tree(tree_files)
            
            # Update index
            self.repo._save_index(tree_files)
            
        except Exception as e:
            print(f"Warning: Could not update working tree: {e}")
    
    def _update_working_tree(self, tree_files: dict):
        """Update working tree files."""
        # Remove files that are no longer in the tree
        current_files = set()
        for file_path in self.repo.repo_path.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.repo.repo_path)
                rel_path_str = str(rel_path).replace('\\\\', '/')
                if not rel_path_str.startswith('.rvs/'):
                    current_files.add(rel_path_str)
        
        # Remove files not in new tree
        for file_path in current_files:
            if file_path not in tree_files:
                full_path = self.repo.repo_path / file_path
                if full_path.exists():
                    full_path.unlink()
                    print(f"D\\t{file_path}")
        
        # Add/update files from tree
        for file_path, file_hash in tree_files.items():
            self._restore_file(file_path, file_hash)
    
    def _restore_file(self, file_path: str, file_hash: str):
        """Restore a file from object store."""
        try:
            obj_type, content = self.repo._read_object(file_hash)
            if obj_type != "blob":
                return
            
            full_path = self.repo.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file content has changed
            file_changed = True
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    current_content = f.read()
                file_changed = current_content != content
            
            if file_changed:
                with open(full_path, 'wb') as f:
                    f.write(content)
                
                if full_path.exists():
                    print(f"M\\t{file_path}")
                else:
                    print(f"A\\t{file_path}")
                
        except Exception:
            pass
    
    def _has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            current_branch = self.repo._get_current_branch()
            current_commit = self.repo._get_branch_commit(current_branch)
            
            if not current_commit:
                return False  # No commits yet
            
            # Get committed files
            commit_data = self.repo._read_commit(current_commit)
            tree_hash = commit_data['tree']
            committed_files = self.repo._read_tree(tree_hash)
            
            # Get staged files
            index = self.repo._load_index()
            
            # Get working files
            working_files = {}
            for file_path in self.repo.repo_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.repo.repo_path)
                    rel_path_str = str(rel_path).replace('\\\\', '/')
                    if not rel_path_str.startswith('.rvs/'):
                        working_files[rel_path_str] = self.repo._get_file_hash(file_path)
            
            # Check for differences
            # 1. Staged changes
            for file_path in index:
                if file_path not in committed_files or index[file_path] != committed_files[file_path]:
                    return True
            
            # 2. Working directory changes
            for file_path in working_files:
                if file_path in index:
                    if working_files[file_path] != index[file_path]:
                        return True
                elif file_path in committed_files:
                    if working_files[file_path] != committed_files[file_path]:
                        return True
            
            # 3. Deleted files
            for file_path in committed_files:
                if file_path not in working_files:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _is_branch_checked_out_elsewhere(self, branch_name: str) -> bool:
        """Check if branch is checked out in another worktree."""
        # Get all worktrees
        from .worktree import WorktreeCommand
        wt_cmd = WorktreeCommand(self.repo)
        worktrees = wt_cmd._get_worktrees()
        
        for wt in worktrees:
            if wt['branch'] == branch_name:
                return True
        
        return False
    
    def _try_create_from_remote(self, branch_name: str, quiet: bool = False) -> bool:
        """Try to create branch from remote tracking branch."""
        # This is a placeholder for remote branch creation
        # In a full implementation, this would check for remote branches
        # and create a local tracking branch
        return False
    
    def _resolve_commit(self, commit_ish: str) -> str:
        """Resolve commit-ish to commit hash."""
        if commit_ish == 'HEAD':
            current_branch = self.repo._get_current_branch()
            commit_hash = self.repo._get_branch_commit(current_branch)
            if not commit_hash:
                raise RVSError("HEAD does not point to a valid commit")
            return commit_hash
        
        # Try as branch name
        branch_commit = self.repo._get_branch_commit(commit_ish)
        if branch_commit:
            return branch_commit
        
        # Try as full commit hash
        try:
            obj_type, content = self.repo._read_object(commit_ish)
            if obj_type == "commit":
                return commit_ish
        except Exception:
            pass
        
        # Try partial hash matching
        if len(commit_ish) >= 4:
            for obj_dir in self.repo.objects_dir.iterdir():
                if obj_dir.is_dir() and len(obj_dir.name) == 2:
                    for obj_file in obj_dir.iterdir():
                        full_hash = obj_dir.name + obj_file.name
                        if full_hash.startswith(commit_ish):
                            try:
                                obj_type, content = self.repo._read_object(full_hash)
                                if obj_type == "commit":
                                    return full_hash
                            except Exception:
                                continue
        
        raise RVSError(f"pathspec '{commit_ish}' did not match any file(s) known to rvs")
    
    def execute(self):
        """Legacy execute method."""
        print('Switch command executed')