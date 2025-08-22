"""Worktree command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List, Optional
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class WorktreeCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('worktree', help='Manage multiple working trees')
        subparsers_wt = parser.add_subparsers(dest='worktree_command', help='Worktree commands')
        
        # add subcommand
        add_parser = subparsers_wt.add_parser('add', help='Create a new working tree')
        add_parser.add_argument('path', help='Path for the new working tree')
        add_parser.add_argument('commit_ish', nargs='?', help='Commit-ish to checkout')
        add_parser.add_argument('-b', '--new-branch', help='Create a new branch')
        add_parser.add_argument('-B', '--force-new-branch', help='Create/reset a new branch')
        add_parser.add_argument('--detach', action='store_true', help='Detach HEAD in new working tree')
        add_parser.add_argument('-f', '--force', action='store_true', help='Force creation')
        
        # list subcommand
        list_parser = subparsers_wt.add_parser('list', help='List details of each working tree')
        list_parser.add_argument('--porcelain', action='store_true', help='Machine-readable output')
        list_parser.add_argument('-v', '--verbose', action='store_true', help='Show additional info')
        
        # remove subcommand
        remove_parser = subparsers_wt.add_parser('remove', help='Remove a working tree')
        remove_parser.add_argument('worktree', help='Working tree to remove')
        remove_parser.add_argument('-f', '--force', action='store_true', help='Force removal')
        
        # prune subcommand
        prune_parser = subparsers_wt.add_parser('prune', help='Prune working tree information')
        prune_parser.add_argument('-n', '--dry-run', action='store_true', help='Do not remove anything')
        prune_parser.add_argument('-v', '--verbose', action='store_true', help='Report all removals')
        
        # move subcommand
        move_parser = subparsers_wt.add_parser('move', help='Move a working tree')
        move_parser.add_argument('worktree', help='Working tree to move')
        move_parser.add_argument('new_path', help='New path for the working tree')
        
        # lock subcommand
        lock_parser = subparsers_wt.add_parser('lock', help='Lock a working tree')
        lock_parser.add_argument('worktree', help='Working tree to lock')
        lock_parser.add_argument('--reason', help='Reason for locking')
        
        # unlock subcommand
        unlock_parser = subparsers_wt.add_parser('unlock', help='Unlock a working tree')
        unlock_parser.add_argument('worktree', help='Working tree to unlock')
        
        return parser
    
    def execute_from_args(self, args: Any):
        if not hasattr(args, 'worktree_command') or not args.worktree_command:
            self.list_worktrees()
        elif args.worktree_command == 'add':
            self.add_worktree(
                path=args.path,
                commit_ish=args.commit_ish,
                new_branch=args.new_branch,
                force_new_branch=args.force_new_branch,
                detach=args.detach,
                force=args.force
            )
        elif args.worktree_command == 'list':
            self.list_worktrees(porcelain=args.porcelain, verbose=args.verbose)
        elif args.worktree_command == 'remove':
            self.remove_worktree(args.worktree, force=args.force)
        elif args.worktree_command == 'prune':
            self.prune_worktrees(dry_run=args.dry_run, verbose=args.verbose)
        elif args.worktree_command == 'move':
            self.move_worktree(args.worktree, args.new_path)
        elif args.worktree_command == 'lock':
            self.lock_worktree(args.worktree, reason=args.reason)
        elif args.worktree_command == 'unlock':
            self.unlock_worktree(args.worktree)
    
    def add_worktree(self, path: str, commit_ish: Optional[str] = None,
                     new_branch: Optional[str] = None, force_new_branch: Optional[str] = None,
                     detach: bool = False, force: bool = False):
        """Add a new working tree."""
        self.repo._ensure_repo_exists()
        
        worktree_path = Path(path).resolve()
        
        # Check if path already exists
        if worktree_path.exists() and not force:
            if any(worktree_path.iterdir()):
                raise RVSError(f"'{path}' already exists and is not empty")
        
        # Create worktree directory
        worktree_path.mkdir(parents=True, exist_ok=True)
        
        # Determine what to checkout
        if force_new_branch:
            branch_name = force_new_branch
            commit_to_checkout = commit_ish or 'HEAD'
        elif new_branch:
            branch_name = new_branch
            commit_to_checkout = commit_ish or 'HEAD'
        elif commit_ish:
            if detach:
                branch_name = None
                commit_to_checkout = commit_ish
            else:
                # Check if commit_ish is a branch name or commit hash
                if self.repo._get_branch_commit(commit_ish):
                    # It's a branch name
                    branch_name = commit_ish
                    commit_to_checkout = commit_ish
                else:
                    # It's a commit hash - create detached HEAD
                    branch_name = None
                    commit_to_checkout = commit_ish
                    detach = True
        else:
            # Default to current branch
            branch_name = self.repo._get_current_branch()
            commit_to_checkout = 'HEAD'
        
        # Resolve commit
        commit_hash = self._resolve_commit(commit_to_checkout)
        
        # Create new branch if requested
        if new_branch or force_new_branch:
            if force_new_branch or not self.repo._get_branch_commit(branch_name):
                self.repo._set_branch_commit(branch_name, commit_hash)
                print(f"Created branch '{branch_name}'")
        
        # Create worktree structure (Git-like)
        # 1. Create worktree metadata directory in main repo
        worktrees_dir = self.repo.rvs_dir / 'worktrees'
        worktrees_dir.mkdir(exist_ok=True)
        
        worktree_name = worktree_path.name
        worktree_metadata_dir = worktrees_dir / worktree_name
        worktree_metadata_dir.mkdir(exist_ok=True)
        
        # 2. Create .rvs file in worktree (pointing to metadata directory)
        rvs_file = worktree_path / '.rvs'
        with open(rvs_file, 'w') as f:
            f.write(f"rvsdir: {worktree_metadata_dir}")
        
        # 3. Create gitdir file in metadata directory (pointing back to main repo)
        gitdir_file = worktree_metadata_dir / 'gitdir'
        with open(gitdir_file, 'w') as f:
            f.write(str(self.repo.rvs_dir))
        
        # 4. Create HEAD file in metadata directory
        head_file = worktree_metadata_dir / 'HEAD'
        if detach or not branch_name:
            with open(head_file, 'w') as f:
                f.write(commit_hash)
        else:
            with open(head_file, 'w') as f:
                f.write(f"ref: refs/heads/{branch_name}")
        
        # Checkout files to worktree
        checked_out_files = self._checkout_files_to_worktree(commit_hash, worktree_path)
        
        # Create index for worktree that matches the checked out files
        self._create_worktree_index(worktree_metadata_dir, checked_out_files)
        
        if detach:
            print(f"Prepared worktree (detached HEAD {commit_hash[:8]})")
        else:
            print(f"Prepared worktree (branch '{branch_name}')")
        print(f"HEAD is now at {commit_hash[:8]}")
    
    def list_worktrees(self, porcelain: bool = False, verbose: bool = False):
        """List all working trees."""
        self.repo._ensure_repo_exists()
        
        # Get current branch and commit info
        current_branch = self.repo._get_current_branch()
        commit_hash = self.repo._get_branch_commit(current_branch)
        
        if not commit_hash:
            commit_hash = "0000000"
        
        # Get additional worktrees
        worktrees = self._get_worktrees()
        
        if porcelain:
            # Porcelain format
            print(f"worktree {self.repo.repo_path}")
            print(f"HEAD {commit_hash}")
            print(f"branch refs/heads/{current_branch}")
            
            for wt in worktrees:
                print(f"worktree {wt['path']}")
                print(f"HEAD {wt['commit']}")
                if wt['branch']:
                    print(f"branch refs/heads/{wt['branch']}")
                else:
                    print("detached")
        else:
            # Regular format (like Git)
            short_hash = commit_hash[:7] if commit_hash != "0000000" else commit_hash
            print(f"{self.repo.repo_path}  {short_hash} [{current_branch}]")
            
            for wt in worktrees:
                short_hash = wt['commit'][:7] if wt['commit'] != "0000000" else wt['commit']
                branch_info = f"[{wt['branch']}]" if wt['branch'] else "[detached]"
                print(f"{wt['path']}  {short_hash} {branch_info}")
    
    def remove_worktree(self, worktree_path: str, force: bool = False):
        """Remove a working tree."""
        self.repo._ensure_repo_exists()
        
        wt_path = Path(worktree_path).resolve()
        
        if not wt_path.exists():
            raise RVSError(f"'{worktree_path}' does not exist")
        
        # Check if it's a valid worktree (has .rvs file)
        rvs_file = wt_path / '.rvs'
        if not rvs_file.is_file():
            raise RVSError(f"'{worktree_path}' is not a working tree")
        
        # Check if worktree is locked
        if self._is_worktree_locked(wt_path) and not force:
            raise RVSError(f"'{worktree_path}' is locked")
        
        # Remove worktree directory
        import shutil
        shutil.rmtree(wt_path)
        
        # Unregister worktree
        self._unregister_worktree(wt_path)
        
        print(f"Removed worktree '{worktree_path}'")
    
    def prune_worktrees(self, dry_run: bool = False, verbose: bool = False):
        """Prune working tree information."""
        self.repo._ensure_repo_exists()
        
        worktrees = self._get_worktrees()
        pruned = []
        
        for wt in worktrees:
            wt_path = Path(wt['path'])
            if not wt_path.exists():
                pruned.append(wt['path'])
                if not dry_run:
                    self._unregister_worktree(wt_path)
        
        if verbose or dry_run:
            for path in pruned:
                action = "would prune" if dry_run else "pruned"
                print(f"{action} {path}")
        
        if not dry_run and pruned:
            print(f"Pruned {len(pruned)} worktree(s)")
    
    def move_worktree(self, worktree_path: str, new_path: str):
        """Move a working tree."""
        print(f"Move worktree from {worktree_path} to {new_path} (not implemented)")
    
    def lock_worktree(self, worktree_path: str, reason: Optional[str] = None):
        """Lock a working tree."""
        wt_path = Path(worktree_path).resolve()
        rvs_file = wt_path / '.rvs'
        
        if rvs_file.is_file():
            with open(rvs_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('rvsdir: '):
                    metadata_dir = Path(content[8:])
                    lock_file = metadata_dir / 'locked'
                    
                    with open(lock_file, 'w') as f:
                        if reason:
                            f.write(reason)
                    
                    print(f"Locked worktree '{worktree_path}'")
                    return
        
        raise RVSError(f"'{worktree_path}' is not a valid worktree")
    
    def unlock_worktree(self, worktree_path: str):
        """Unlock a working tree."""
        wt_path = Path(worktree_path).resolve()
        rvs_file = wt_path / '.rvs'
        
        if rvs_file.is_file():
            with open(rvs_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('rvsdir: '):
                    metadata_dir = Path(content[8:])
                    lock_file = metadata_dir / 'locked'
                    
                    if lock_file.exists():
                        lock_file.unlink()
                        print(f"Unlocked worktree '{worktree_path}'")
                    else:
                        print(f"Worktree '{worktree_path}' is not locked")
                    return
        
        raise RVSError(f"'{worktree_path}' is not a valid worktree")
    
    def _checkout_files_to_worktree(self, commit_hash: str, worktree_path: Path):
        """Checkout files from commit to worktree."""
        checked_out_files = {}
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return checked_out_files
            
            import json
            commit_data = json.loads(content.decode('utf-8'))
            tree_hash = commit_data['tree']
            tree_files = self.repo._read_tree(tree_hash)
            
            for file_path, file_hash in tree_files.items():
                if self._restore_file_to_worktree(file_path, file_hash, worktree_path):
                    checked_out_files[file_path] = file_hash
                
        except Exception as e:
            print(f"Warning: Could not checkout files: {e}")
        
        return checked_out_files
    
    def _restore_file_to_worktree(self, file_path: str, file_hash: str, worktree_path: Path):
        """Restore a file to specific worktree."""
        try:
            obj_type, content = self.repo._read_object(file_hash)
            if obj_type != "blob":
                return False
            
            full_path = worktree_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(content)
            
            return True
                
        except Exception:
            return False
    
    def _create_worktree_index(self, worktree_metadata_dir: Path, checked_out_files: dict):
        """Create an index file for the worktree that matches the checked out files."""
        from ..core.index import Index
        
        # Create index in the worktree metadata directory
        # We need to create a temporary repo path for the Index class
        # The Index class expects the repo path, but we want to save to a specific location
        index_file = worktree_metadata_dir / 'index'
        
        # Convert checked_out_files to the format expected by Index
        entries = {}
        for file_path, file_hash in checked_out_files.items():
            entries[file_path] = {'obj_hash': file_hash}
        
        # Save the index directly to the metadata directory
        import json
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
    

    
    def _unregister_worktree(self, worktree_path: Path):
        """Unregister a worktree."""
        worktrees_dir = self.repo.rvs_dir / 'worktrees'
        if not worktrees_dir.exists():
            return
        
        wt_name = worktree_path.name
        wt_info_dir = worktrees_dir / wt_name
        
        if wt_info_dir.exists():
            import shutil
            shutil.rmtree(wt_info_dir)
    
    def _get_worktrees(self) -> List[dict]:
        """Get list of registered worktrees."""
        worktrees = []
        worktrees_dir = self.repo.rvs_dir / 'worktrees'
        
        if not worktrees_dir.exists():
            return worktrees
        
        for wt_dir in worktrees_dir.iterdir():
            if wt_dir.is_dir():
                gitdir_file = wt_dir / 'gitdir'
                head_file = wt_dir / 'HEAD'
                
                if gitdir_file.exists() and head_file.exists():
                    try:
                        with open(gitdir_file, 'r') as f:
                            gitdir_path = f.read().strip()
                        
                        wt_path = Path(gitdir_path).parent
                        
                        with open(head_file, 'r') as f:
                            head_content = f.read().strip()
                        
                        if head_content.startswith('ref: refs/heads/'):
                            branch = head_content[16:]
                            commit = self.repo._get_branch_commit(branch) or '0000000'
                        else:
                            branch = None
                            commit = head_content
                        
                        worktrees.append({
                            'path': str(wt_path),
                            'branch': branch,
                            'commit': commit
                        })
                    except Exception:
                        continue  # Skip invalid worktree entries
        
        return worktrees
    
    def _is_worktree_locked(self, worktree_path: Path) -> bool:
        """Check if worktree is locked."""
        # For new-style worktrees, check in the metadata directory
        rvs_file = worktree_path / '.rvs'
        if rvs_file.is_file():
            with open(rvs_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('rvsdir: '):
                    metadata_dir = Path(content[8:])
                    lock_file = metadata_dir / 'locked'
                    return lock_file.exists()
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
        if len(commit_ish) >= 4:  # Minimum partial hash length
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
        
        raise RVSError(f"Not a valid commit: {commit_ish}")
    
    def execute(self):
        """Legacy execute method."""
        print('Worktree command executed')