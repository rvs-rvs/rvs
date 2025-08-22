"""Diff-tree command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from .base import BaseCommand
from ..exceptions import RVSError

class DiffTreeCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('diff-tree', help='Compare trees')
        parser.add_argument('tree_ish', nargs='*', 
                          help='Tree-ish objects to compare')
        parser.add_argument('--no-commit-id', action='store_true',
                          help='Do not output commit ID')
        parser.add_argument('--name-status', action='store_true',
                          help='Show only names and status of changed files')
        parser.add_argument('--name-only', action='store_true',
                          help='Show only names of changed files')
        parser.add_argument('-r', '--recursive', action='store_true',
                          help='Recurse into subdirectories')
        parser.add_argument('-t', '--show-tree-entry-names', action='store_true',
                          help='Show tree entry names')
        return parser
    
    def execute_from_args(self, args: Any):
        if not args.tree_ish:
            # Default to HEAD
            args.tree_ish = ['HEAD']
        
        if len(args.tree_ish) == 1:
            # Compare with parent
            self.diff_tree_with_parent(args.tree_ish[0],
                                     no_commit_id=args.no_commit_id,
                                     name_status=args.name_status,
                                     name_only=args.name_only)
        else:
            # Compare two trees
            self.diff_trees(args.tree_ish[0], args.tree_ish[1],
                          no_commit_id=args.no_commit_id,
                          name_status=args.name_status,
                          name_only=args.name_only)
    
    def diff_tree_with_parent(self, commit_ref: str, no_commit_id: bool = False,
                            name_status: bool = False, name_only: bool = False):
        """Compare a commit with its parent."""
        self.repo._ensure_repo_exists()
        
        # Resolve commit
        commit_hash = self._resolve_commit(commit_ref)
        
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                raise RVSError(f"Not a commit: {commit_ref}")
            
            import json
            commit_data = json.loads(content.decode())
            
            # Get parent commit
            parent_hash = commit_data.get('parent')
            
            if not no_commit_id:
                print(commit_hash)
            
            # Get current tree
            current_tree = self.repo._read_tree(commit_data['tree'])
            
            # Get parent tree
            parent_tree = {}
            if parent_hash:
                try:
                    parent_obj_type, parent_content = self.repo._read_object(parent_hash)
                    if parent_obj_type == "commit":
                        parent_commit_data = json.loads(parent_content.decode())
                        parent_tree = self.repo._read_tree(parent_commit_data['tree'])
                except Exception:
                    pass
            
            # Show differences
            self._show_tree_diff(parent_tree, current_tree, name_status, name_only)
            
        except Exception as e:
            raise RVSError(f"Could not diff tree {commit_ref}: {e}")
    
    def diff_trees(self, tree1_ref: str, tree2_ref: str, no_commit_id: bool = False,
                  name_status: bool = False, name_only: bool = False):
        """Compare two trees."""
        self.repo._ensure_repo_exists()
        
        # Resolve trees
        tree1_hash = self._resolve_tree(tree1_ref)
        tree2_hash = self._resolve_tree(tree2_ref)
        
        # Get tree contents
        tree1_files = self.repo._read_tree(tree1_hash)
        tree2_files = self.repo._read_tree(tree2_hash)
        
        # Show differences
        self._show_tree_diff(tree1_files, tree2_files, name_status, name_only)
    
    def _show_tree_diff(self, old_tree: dict, new_tree: dict, 
                       name_status: bool, name_only: bool):
        """Show differences between two trees."""
        # Calculate changes
        added_files = []
        modified_files = []
        deleted_files = []
        
        # Find added and modified files
        for file_path, file_hash in new_tree.items():
            if file_path not in old_tree:
                added_files.append(file_path)
            elif old_tree[file_path] != file_hash:
                modified_files.append(file_path)
        
        # Find deleted files
        for file_path in old_tree.keys():
            if file_path not in new_tree:
                deleted_files.append(file_path)
        
        # Show output based on options
        if name_status:
            for file_path in sorted(added_files):
                print(f"A\\t{file_path}")
            for file_path in sorted(modified_files):
                print(f"M\\t{file_path}")
            for file_path in sorted(deleted_files):
                print(f"D\\t{file_path}")
        elif name_only:
            all_changed = sorted(added_files + modified_files + deleted_files)
            for file_path in all_changed:
                print(file_path)
        else:
            # Show detailed diff (simplified)
            for file_path in sorted(added_files):
                old_hash = "0000000"
                new_hash = new_tree[file_path][:7]
                print(f":000000 100644 {old_hash} {new_hash} A\\t{file_path}")
            
            for file_path in sorted(modified_files):
                old_hash = old_tree[file_path][:7]
                new_hash = new_tree[file_path][:7]
                print(f":100644 100644 {old_hash} {new_hash} M\\t{file_path}")
            
            for file_path in sorted(deleted_files):
                old_hash = old_tree[file_path][:7]
                new_hash = "0000000"
                print(f":100644 000000 {old_hash} {new_hash} D\\t{file_path}")
    
    def _resolve_commit(self, commit_ref: str) -> str:
        """Resolve commit reference to hash."""
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
    
    def _resolve_tree(self, tree_ref: str) -> str:
        """Resolve tree reference to hash."""
        # If it's a commit, get its tree
        try:
            commit_hash = self._resolve_commit(tree_ref)
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type == "commit":
                import json
                commit_data = json.loads(content.decode())
                return commit_data['tree']
        except Exception:
            pass
        
        # Try as direct tree hash
        try:
            obj_type, content = self.repo._read_object(tree_ref)
            if obj_type == "tree":
                return tree_ref
        except Exception:
            pass
        
        raise RVSError(f"Not a valid tree: {tree_ref}")
    
    def execute(self):
        """Legacy execute method."""
        self.diff_tree_with_parent('HEAD')