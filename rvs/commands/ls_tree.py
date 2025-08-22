"""LsTree command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, Optional, List, Tuple
from .base import BaseCommand
from ..exceptions import RVSError

class LsTreeCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('ls-tree', help='List the contents of a tree object')
        parser.add_argument('tree_ish', nargs='?', default='HEAD', 
                          help='Tree-ish object to list (commit, branch, or tree hash)')
        parser.add_argument('--name-only', action='store_true', 
                          help='List only filenames')
        parser.add_argument('-r', '--recursive', action='store_true', 
                          help='Recurse into sub-trees')
        parser.add_argument('-t', '--show-trees', action='store_true', 
                          help='Show tree entries even when going to recurse them')
        parser.add_argument('-l', '--long', action='store_true', 
                          help='Show object size for blobs')
        return parser
    
    def execute_from_args(self, args: Any):
        self.ls_tree(args.tree_ish, args.name_only, args.recursive, 
                    args.show_trees, args.long)
    
    def ls_tree(self, tree_ish: str = "HEAD", name_only: bool = False, 
                recursive: bool = False, show_trees: bool = False, 
                long_format: bool = False):
        """List the contents of a tree object (similar to git ls-tree)."""
        self.repo._ensure_repo_exists()
        
        # Resolve tree-ish to tree hash
        tree_hash = self._resolve_tree_ish(tree_ish)
        if not tree_hash:
            raise RVSError(f"Not a valid object name {tree_ish}")
        
        try:
            self._list_tree_contents(tree_hash, name_only, recursive, 
                                   show_trees, long_format)
        except Exception as e:
            raise RVSError(f"Error listing tree contents: {e}")
    
    def _resolve_tree_ish(self, tree_ish: str) -> Optional[str]:
        """Resolve a tree-ish (branch, commit, or tree hash) to a tree hash."""
        commit_hash = self._resolve_commit_ish(tree_ish)
        if not commit_hash:
            return None
        
        # Get tree hash from commit
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type == "commit":
                import json
                commit_data = json.loads(content.decode('utf-8'))
                return commit_data.get("tree")
            elif obj_type == "tree":
                return commit_hash
            else:
                return None
        except Exception:
            return None
    
    def _resolve_commit_ish(self, commit_ish: str) -> Optional[str]:
        """Resolve a commit-ish (HEAD, branch, or commit hash) to a commit hash."""
        if commit_ish == "HEAD":
            # Get current branch and its commit
            current_branch = self.repo._get_current_branch()
            commit_hash = self.repo._get_branch_commit(current_branch)
            return commit_hash
        
        # Try as branch name first
        branch_commit = self.repo._get_branch_commit(commit_ish)
        if branch_commit:
            return branch_commit
        
        # Check if it's a commit hash
        try:
            obj_type, content = self.repo._read_object(commit_ish)
            if obj_type == "commit":
                return commit_ish
            else:
                return None
        except Exception:
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
            return None
    
    def _list_tree_contents(self, tree_hash: str, name_only: bool = False, 
                           recursive: bool = False, show_trees: bool = False, 
                           long_format: bool = False, prefix: str = ""):
        """List contents of a tree object."""
        try:
            # Read tree files using the repository's _read_tree method
            tree_files = self.repo._read_tree(tree_hash)
            
            if not tree_files:
                return
            
            # Convert to entries format for processing
            entries = []
            subdirs = {}
            
            for file_path, file_hash in tree_files.items():
                if '/' in file_path:
                    # File is in a subdirectory
                    parts = file_path.split('/', 1)
                    subdir_name = parts[0]
                    remaining_path = parts[1]
                    
                    if subdir_name not in subdirs:
                        subdirs[subdir_name] = {}
                    subdirs[subdir_name][remaining_path] = file_hash
                else:
                    # File in current directory
                    entries.append(("blob", file_hash, file_path))
            
            # Add subdirectories as tree entries
            for subdir_name in subdirs.keys():
                # For simplicity, we'll use a placeholder hash for subdirectories
                # In a full implementation, we'd need to create proper tree objects for subdirs
                entries.append(("tree", "0000000000000000000000000000000000000000", subdir_name))
            
            # Sort entries (trees first, then blobs, both alphabetically)
            entries.sort(key=lambda x: (x[0] != "tree", x[2]))
            
            if recursive:
                # Recursive mode: show all files with full paths
                for file_path, file_hash in sorted(tree_files.items()):
                    full_path = prefix + file_path if prefix else file_path
                    if name_only:
                        print(full_path)
                    else:
                        mode = "100644"  # Default file mode for blobs
                        print(f"{mode} blob {file_hash}\\t{full_path}")
            else:
                # Non-recursive mode: show current level only
                for obj_type, obj_hash, filename in entries:
                    full_path = prefix + filename if prefix else filename
                    
                    if name_only:
                        print(full_path)
                    else:
                        if obj_type == "tree":
                            mode = "040000"
                        else:
                            mode = "100644"
                        
                        print(f"{mode} {obj_type} {obj_hash}\\t{full_path}")
        
        except Exception as e:
            raise Exception(f"Failed to read tree {tree_hash}: {e}")