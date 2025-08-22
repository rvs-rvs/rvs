"""Restore command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List, Optional
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class RestoreCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('restore', help='Restore working tree files')
        parser.add_argument('pathspec', nargs='*', help='Files to restore')
        parser.add_argument('-s', '--source', 
                          help='Restore from this tree-ish')
        parser.add_argument('-S', '--staged', action='store_true',
                          help='Restore the index')
        parser.add_argument('-W', '--worktree', action='store_true',
                          help='Restore the working tree (default)')
        parser.add_argument('--pathspec-from-file', 
                          help='Read pathspec from file')
        return parser
    
    def execute_from_args(self, args: Any):
        self.restore(
            pathspec=args.pathspec,
            source=args.source,
            staged=args.staged,
            worktree=args.worktree,
            pathspec_from_file=args.pathspec_from_file
        )
    
    def restore(self, pathspec: List[str] = None, source: str = None,
                staged: bool = False, worktree: bool = False,
                pathspec_from_file: Optional[str] = None):
        """Restore working tree files."""
        self.repo._ensure_repo_exists()
        
        # Default to worktree if neither specified
        if not staged and not worktree:
            worktree = True
        
        # Get pathspec
        if pathspec_from_file:
            try:
                with open(pathspec_from_file, 'r') as f:
                    pathspec = [line.strip() for line in f if line.strip()]
            except IOError as e:
                raise RVSError(f"Cannot read pathspec file: {e}")
        
        if not pathspec:
            pathspec = ['.']  # Default to current directory
        
        # Determine source based on what we're restoring
        if not source:
            if staged:
                # Restoring to index: default source is HEAD
                source = 'HEAD'
            else:
                # Restoring to worktree: default source is index, but if index is empty, use HEAD
                index = self.repo._load_index()
                if not index:
                    # Index is empty, restore from HEAD
                    source = 'HEAD'
                else:
                    # Restore from index
                    self._restore_from_index(pathspec, worktree)
                    return
        
        # Resolve source commit
        source_commit = self._resolve_commit(source)
        
        if staged:
            self._restore_to_index(pathspec, source_commit)
        if worktree:
            self._restore_to_worktree(pathspec, source_commit)
    
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
    
    def _restore_from_index(self, pathspec: List[str], worktree: bool):
        """Restore files from index to working tree."""
        index = self.repo._load_index()
        
        if not index:
            # Index is empty, try to restore from HEAD instead
            print("Index is empty, restoring from HEAD instead")
            try:
                source_commit = self._resolve_commit('HEAD')
                self._restore_to_worktree(pathspec, source_commit)
                return
            except RVSError:
                print("No commits found to restore from")
                return
        
        found_any = False
        for pattern in pathspec:
            if pattern == '.':
                # Restore all files in index
                for file_path, file_hash in index.items():
                    self._restore_file_from_hash(file_path, file_hash)
                    # Git restore is silent
                    found_any = True
            else:
                # Restore specific file
                if pattern in index:
                    self._restore_file_from_hash(pattern, index[pattern])
                    # Git restore is silent
                    found_any = True
                else:
                    # Try to find the file in HEAD if not in index
                    try:
                        source_commit = self._resolve_commit('HEAD')
                        obj_type, content = self.repo._read_object(source_commit)
                        if obj_type == "commit":
                            import json
                            commit_data = json.loads(content.decode())
                            tree_hash = commit_data['tree']
                            tree_files = self.repo._read_tree(tree_hash)
                            
                            if pattern in tree_files:
                                self._restore_file_from_hash(pattern, tree_files[pattern])
                                # Git restore is silent
                                found_any = True
                            else:
                                print(f"pathspec '{pattern}' did not match any files")
                    except Exception:
                        print(f"pathspec '{pattern}' did not match any files")
        
        if not found_any and len(pathspec) == 1 and pathspec[0] != '.':
            print(f"pathspec '{pathspec[0]}' did not match any files")
    
    def _restore_to_index(self, pathspec: List[str], source_commit: str):
        """Restore files from commit to index."""
        # Get tree from commit
        obj_type, content = self.repo._read_object(source_commit)
        if obj_type != "commit":
            raise RVSError(f"Not a commit: {source_commit}")
        
        import json
        commit_data = json.loads(content.decode())
        tree_hash = commit_data['tree']
        tree_files = self.repo._read_tree(tree_hash)
        
        # Load current index
        index = self.repo._load_index()
        
        for pattern in pathspec:
            if pattern == '.':
                # Restore all files from tree to index
                for file_path, file_hash in tree_files.items():
                    index[file_path] = file_hash
                    # Git restore is silent
            else:
                # Restore specific file
                if pattern in tree_files:
                    index[pattern] = tree_files[pattern]
                    # Git restore is silent
                else:
                    # Remove from index if not in source
                    if pattern in index:
                        del index[pattern]
                        # Git restore is silent
                    else:
                        print(f"pathspec '{pattern}' did not match any files")
        
        # Save updated index
        self.repo._save_index(index)
    
    def _restore_to_worktree(self, pathspec: List[str], source_commit: str):
        """Restore files from commit to working tree."""
        # Get tree from commit
        obj_type, content = self.repo._read_object(source_commit)
        if obj_type != "commit":
            raise RVSError(f"Not a commit: {source_commit}")
        
        import json
        commit_data = json.loads(content.decode())
        tree_hash = commit_data['tree']
        tree_files = self.repo._read_tree(tree_hash)
        
        for pattern in pathspec:
            if pattern == '.':
                # Restore all files from tree
                for file_path, file_hash in tree_files.items():
                    self._restore_file_from_hash(file_path, file_hash)
                    # Git restore is silent
            else:
                # Restore specific file
                if pattern in tree_files:
                    self._restore_file_from_hash(pattern, tree_files[pattern])
                    # Git restore is silent
                else:
                    print(f"pathspec '{pattern}' did not match any files")
    
    def _restore_file_from_hash(self, file_path: str, file_hash: str):
        """Restore a file from its hash to working tree."""
        try:
            obj_type, content = self.repo._read_object(file_hash)
            if obj_type != "blob":
                raise RVSError(f"Expected blob, got {obj_type}")
            
            # Create directory if needed
            full_path = self.repo.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(full_path, 'wb') as f:
                f.write(content)
                
        except Exception as e:
            raise RVSError(f"Failed to restore {file_path}: {e}")
