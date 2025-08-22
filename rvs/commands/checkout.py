"""Checkout command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List, Optional
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class CheckoutCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('checkout', help='Switch branches or restore working tree files')
        parser.add_argument('branch_or_commit', nargs='?', 
                          help='Branch name or commit to checkout')
        parser.add_argument('pathspec', nargs='*', 
                          help='Limit checkout to specific paths')
        parser.add_argument('-b', '--create-branch', 
                          help='Create and checkout a new branch')
        parser.add_argument('-B', '--force-create-branch',
                          help='Create/reset and checkout a branch')
        parser.add_argument('-f', '--force', action='store_true',
                          help='Force checkout (lose local changes)')
        parser.add_argument('--detach', action='store_true',
                          help='Detach HEAD at named commit')
        return parser
    
    def execute_from_args(self, args: Any):
        if args.create_branch:
            self.checkout_new_branch(args.create_branch, args.branch_or_commit)
        elif args.force_create_branch:
            self.checkout_new_branch(args.force_create_branch, args.branch_or_commit, force=True)
        elif args.pathspec:
            self.checkout_paths(args.branch_or_commit or 'HEAD', args.pathspec)
        elif args.branch_or_commit:
            self.checkout_branch(args.branch_or_commit, detach=args.detach, force=args.force)
        else:
            # Show current branch
            self.show_current_branch()
    
    def execute(self, target, files=None):
        """Legacy execute method for compatibility."""
        if files:
            self.checkout_paths(target, files)
        else:
            self.checkout_branch(target)
    
    def show_current_branch(self):
        """Show current branch information."""
        self.repo._ensure_repo_exists()
        current_branch = self.repo._get_current_branch()
        commit_hash = self.repo._get_branch_commit(current_branch)
        
        if commit_hash:
            print(f"On branch {current_branch}")
            print(f"HEAD is at {commit_hash[:8]}")
        else:
            print(f"On branch {current_branch} (no commits yet)")
    
    def checkout_branch(self, branch_or_commit: str, detach: bool = False, force: bool = False):
        """Switch to a branch or commit."""
        self.repo._ensure_repo_exists()
        
        # Check for uncommitted changes
        if not force and self._has_uncommitted_changes():
            raise RVSError("You have uncommitted changes. Use --force to override.")
        
        # Try to resolve as branch first
        branch_commit = self.repo._get_branch_commit(branch_or_commit)
        
        if branch_commit:
            # It's a branch
            if detach:
                self._detach_head(branch_commit)
                import sys
                print(f"HEAD is now at {branch_commit[:8]} (detached)", file=sys.stderr)
            else:
                self._switch_to_branch(branch_or_commit)
                import sys
                print(f"Switched to branch '{branch_or_commit}'", file=sys.stderr)
        else:
            # Try as commit hash
            try:
                commit_hash = self._resolve_commit(branch_or_commit)
                self._detach_head(commit_hash)
                import sys
                print(f"HEAD is now at {commit_hash[:8]} (detached)", file=sys.stderr)
            except RVSError:
                raise RVSError(f"pathspec '{branch_or_commit}' did not match any file(s) known to rvs")
    
    def checkout_new_branch(self, branch_name: str, start_point: Optional[str] = None, force: bool = False):
        """Create and checkout a new branch."""
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
                raise RVSError("Cannot create branch: no commits found")
        
        # Create the branch
        self.repo._set_branch_commit(branch_name, start_commit)
        
        # Switch to the new branch
        self._switch_to_branch(branch_name)
        
        import sys
        if force:
            print(f"Reset branch '{branch_name}' to {start_commit[:8]}", file=sys.stderr)
        else:
            print(f"Switched to a new branch '{branch_name}'", file=sys.stderr)
    
    def checkout_paths(self, tree_ish: str, pathspec: List[str]):
        """Checkout specific paths from a tree-ish."""
        self.repo._ensure_repo_exists()
        
        # Resolve tree-ish to commit
        commit_hash = self._resolve_commit(tree_ish)
        
        # Get tree from commit
        obj_type, content = self.repo._read_object(commit_hash)
        if obj_type != "commit":
            raise RVSError(f"Not a commit: {tree_ish}")
        
        import json
        commit_data = json.loads(content.decode())
        tree_hash = commit_data['tree']
        tree_files = self.repo._read_tree(tree_hash)
        
        # Checkout specified paths
        for path in pathspec:
            if path in tree_files:
                self._restore_file_from_hash(path, tree_files[path])
                print(f"Updated {path}")
            else:
                print(f"pathspec '{path}' did not match any files")
    
    def _switch_to_branch(self, branch_name: str):
        """Switch HEAD to point to a branch."""
        with open(self.repo.head_file, 'w') as f:
            f.write(f"ref: refs/heads/{branch_name}")
        
        # Update working tree to match branch
        commit_hash = self.repo._get_branch_commit(branch_name)
        if commit_hash:
            self._update_working_tree(commit_hash)
            # Update index to match the checked-out commit
            self._update_index_to_commit(commit_hash)
    
    def _detach_head(self, commit_hash: str):
        """Detach HEAD to point directly to a commit."""
        with open(self.repo.head_file, 'w') as f:
            f.write(commit_hash)
        
        # Update working tree to match commit
        self._update_working_tree(commit_hash)
        
        # Update index to match the checked-out commit
        self._update_index_to_commit(commit_hash)
    
    def _update_working_tree(self, commit_hash: str):
        """Update working tree to match a commit."""
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            tree_files = self.repo._read_tree(tree_hash)
            
            # Remove files not in the target commit
            self._clean_working_tree(tree_files)
            
            # Restore all files from the commit
            for file_path, file_hash in tree_files.items():
                self._restore_file_from_hash(file_path, file_hash)
                
        except Exception as e:
            print(f"Warning: Could not update working tree: {e}")
    
    def _clean_working_tree(self, target_files: dict):
        """Remove files from working tree that aren't in target."""
        # Get current working tree files
        current_files = set()
        for file_path in self.repo.repo_path.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.repo.repo_path)
                rel_path_str = str(rel_path)
                
                # Skip .rvs file/directory and its contents
                if rel_path_str == '.rvs' or rel_path_str.startswith('.rvs/'):
                    continue
                
                current_files.add(rel_path_str)
        
        # Remove files not in target
        target_file_set = set(target_files.keys())
        for file_path in current_files - target_file_set:
            try:
                (self.repo.repo_path / file_path).unlink()
                print(f"Removed {file_path}")
            except Exception:
                pass  # Ignore errors
    
    def _restore_file_from_hash(self, file_path: str, file_hash: str):
        """Restore a file from its hash."""
        try:
            obj_type, content = self.repo._read_object(file_hash)
            if obj_type != "blob":
                return
            
            full_path = self.repo.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(content)
                
        except Exception:
            pass  # Ignore errors
    
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
    
    def _has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            current_branch = self.repo._get_current_branch()
            commit_hash = self.repo._get_branch_commit(current_branch)
            if not commit_hash:
                # No commits yet, check if there are staged files
                index = self.repo._load_index()
                return bool(index)
            
            # Get committed files
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return False
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            committed_files = self.repo._read_tree(tree_hash)
            
            # Get staged files
            index = self.repo._load_index()
            
            # Check if index differs from committed files
            if set(index.keys()) != set(committed_files.keys()):
                return True  # Different files staged
            
            for file_path in index.keys():
                if index[file_path] != committed_files.get(file_path):
                    return True  # File content differs
            
            # Check if working tree differs from committed files
            for file_path, committed_hash in committed_files.items():
                full_path = self.repo.repo_path / file_path
                if full_path.exists():
                    current_hash = self.repo._get_file_hash(full_path)
                    if current_hash != committed_hash:
                        return True
                else:
                    return True  # File was deleted
            
            return False
            
        except Exception:
            return False  # Assume no changes if we can't determine
    
    def _update_index_to_commit(self, commit_hash: str):
        """Update the index to match a specific commit."""
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            tree_files = self.repo._read_tree(tree_hash)
            
            # Set index to match the commit's tree
            self.repo._save_index(tree_files)
            
        except Exception:
            pass  # Ignore errors
