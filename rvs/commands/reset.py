"""Reset command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List, Optional
from .base import BaseCommand
from ..exceptions import RVSError

class ResetCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('reset', help='Reset current HEAD to the specified state')
        parser.add_argument('commit', nargs='?', default='HEAD',
                          help='Commit to reset to')
        parser.add_argument('pathspec', nargs='*',
                          help='Limit reset to specific paths')
        parser.add_argument('--soft', action='store_true',
                          help='Reset only HEAD')
        parser.add_argument('--mixed', action='store_true',
                          help='Reset HEAD and index (default)')
        parser.add_argument('--hard', action='store_true',
                          help='Reset HEAD, index, and working tree')
        parser.add_argument('--keep', action='store_true',
                          help='Reset HEAD but keep local changes')
        parser.add_argument('-q', '--quiet', action='store_true',
                          help='Be quiet, only report errors')
        return parser
    
    def execute_from_args(self, args: Any):
        # Determine reset mode
        if args.hard:
            mode = 'hard'
        elif args.soft:
            mode = 'soft'
        elif args.keep:
            mode = 'keep'
        else:
            mode = 'mixed'  # default
        
        if args.pathspec:
            self.reset_paths(args.pathspec, args.commit)
        else:
            self.reset_to_commit(args.commit, mode, quiet=args.quiet)
    
    def reset_to_commit(self, commit_ref: str, mode: str = 'mixed', quiet: bool = False):
        """Reset HEAD to a specific commit."""
        self.repo._ensure_repo_exists()
        
        # Resolve commit
        commit_hash = self._resolve_commit(commit_ref)
        
        # Get current branch
        current_branch = self.repo._get_current_branch()
        
        if current_branch == 'HEAD':
            # In detached HEAD state
            if not quiet:
                print(f"HEAD is now at {commit_hash[:8]}")
        else:
            # On a branch
            if not quiet:
                print(f"HEAD is now at {commit_hash[:8]}")
        
        # Update HEAD
        if current_branch == 'HEAD':
            # Detached HEAD - update HEAD file directly
            with open(self.repo.head_file, 'w') as f:
                f.write(commit_hash)
        else:
            # On a branch - update branch reference
            self.repo._set_branch_commit(current_branch, commit_hash)
        
        if mode in ['mixed', 'hard']:
            # Reset index
            self._reset_index(commit_hash)
        
        if mode == 'hard':
            # Reset working tree
            self._reset_working_tree(commit_hash)
        elif mode == 'keep':
            # Keep local changes but reset HEAD
            pass
    
    def reset_paths(self, pathspec: List[str], tree_ish: str = 'HEAD'):
        """Reset specific paths in the index."""
        self.repo._ensure_repo_exists()
        
        # Resolve tree-ish
        commit_hash = self._resolve_commit(tree_ish)
        
        # Get tree from commit
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                raise RVSError(f"Not a commit: {tree_ish}")
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            tree_files = self.repo._read_tree(tree_hash)
            
            # Load current index
            index = self.repo._load_index()
            
            # Reset specified paths
            for path in pathspec:
                if path in tree_files:
                    index[path] = tree_files[path]
                    print(f"Unstaged changes after reset:")
                    print(f"M\\t{path}")
                elif path in index:
                    # Remove from index if not in tree
                    del index[path]
                    print(f"Unstaged changes after reset:")
                    print(f"D\\t{path}")
                else:
                    print(f"pathspec '{path}' did not match any files")
            
            # Save updated index
            self.repo._save_index(index)
            
        except Exception as e:
            raise RVSError(f"Could not reset paths: {e}")
    
    def _reset_index(self, commit_hash: str):
        """Reset index to match commit."""
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            tree_files = self.repo._read_tree(tree_hash)
            
            # Update index to match tree
            self.repo._save_index(tree_files)
            
        except Exception as e:
            print(f"Warning: Could not reset index: {e}")
    
    def _reset_working_tree(self, commit_hash: str):
        """Reset working tree to match commit."""
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
            print(f"Warning: Could not reset working tree: {e}")
    
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
    
    def _resolve_commit(self, commit_ref: str) -> str:
        """Resolve commit reference to hash."""
        # Handle HEAD~N syntax
        if commit_ref.startswith('HEAD~'):
            try:
                steps_back = int(commit_ref[5:])
                return self._get_ancestor_commit('HEAD', steps_back)
            except ValueError:
                raise RVSError(f"Invalid commit reference: {commit_ref}")
        
        if commit_ref == 'HEAD':
            current_branch = self.repo._get_current_branch()
            commit_hash = self.repo._get_branch_commit(current_branch)
            if not commit_hash:
                raise RVSError("HEAD does not point to a valid commit")
            return commit_hash
        
        # Try as branch name
        branch_commit = self.repo._get_branch_commit(commit_ref)
        if branch_commit:
            return branch_commit
        
        # Try as full hash
        try:
            obj_type, content = self.repo._read_object(commit_ref)
            if obj_type == "commit":
                return commit_ref
        except Exception:
            pass
        
        # Try partial hash matching
        if len(commit_ref) >= 4:
            for obj_dir in self.repo.objects_dir.iterdir():
                if obj_dir.is_dir() and len(obj_dir.name) == 2:
                    for obj_file in obj_dir.iterdir():
                        full_hash = obj_dir.name + obj_file.name
                        if full_hash.startswith(commit_ref):
                            try:
                                obj_type, content = self.repo._read_object(full_hash)
                                if obj_type == "commit":
                                    return full_hash
                            except Exception:
                                continue
        
        raise RVSError(f"Not a valid commit: {commit_ref}")
    
    def _get_ancestor_commit(self, commit_ref: str, steps: int) -> str:
        """Get ancestor commit N steps back."""
        current_hash = self._resolve_commit(commit_ref)
        
        for _ in range(steps):
            try:
                obj_type, content = self.repo._read_object(current_hash)
                if obj_type != "commit":
                    raise RVSError(f"Not enough history")
                
                import json
                commit_data = json.loads(content.decode())
                parent_hash = commit_data.get('parent')
                
                if not parent_hash:
                    raise RVSError(f"Not enough history")
                
                current_hash = parent_hash
                
            except Exception:
                raise RVSError(f"Not enough history")
        
        return current_hash
    
    def execute(self):
        """Legacy execute method."""
        self.reset_to_commit('HEAD')