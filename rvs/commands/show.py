"""Show command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from .base import BaseCommand
from ..exceptions import RVSError

class ShowCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('show', help='Show various types of objects')
        parser.add_argument('object', nargs='?', default='HEAD',
                          help='Object to show (commit, tree, blob)')
        parser.add_argument('--name-status', action='store_true',
                          help='Show only names and status of changed files')
        parser.add_argument('--name-only', action='store_true',
                          help='Show only names of changed files')
        parser.add_argument('--stat', action='store_true',
                          help='Show diffstat')
        parser.add_argument('--no-patch', action='store_true',
                          help='Suppress diff output')
        return parser
    
    def execute_from_args(self, args: Any):
        self.show_object(args.object, 
                        name_status=args.name_status,
                        name_only=args.name_only,
                        stat=args.stat,
                        no_patch=args.no_patch)
    
    def show_object(self, object_ref: str, name_status: bool = False, 
                   name_only: bool = False, stat: bool = False, no_patch: bool = False):
        """Show an object (commit, tree, or blob)."""
        self.repo._ensure_repo_exists()
        
        # Resolve object reference
        obj_hash = self._resolve_object(object_ref)
        
        try:
            obj_type, content = self.repo._read_object(obj_hash)
            
            if obj_type == "commit":
                self._show_commit(obj_hash, content, name_status, name_only, stat, no_patch)
            elif obj_type == "tree":
                self._show_tree(obj_hash, content)
            elif obj_type == "blob":
                self._show_blob(obj_hash, content)
            else:
                raise RVSError(f"Unknown object type: {obj_type}")
                
        except Exception as e:
            raise RVSError(f"Could not show object {object_ref}: {e}")
    
    def _show_commit(self, commit_hash: str, content: bytes, name_status: bool, 
                    name_only: bool, stat: bool, no_patch: bool):
        """Show a commit object."""
        import json
        import time
        import datetime
        
        commit_data = json.loads(content.decode())
        
        # Show commit header
        print(f"commit {commit_hash}")
        print(f"Author: {commit_data.get('author', 'RVS User')} <rvs@example.com>")
        
        # Format date like Git
        timestamp = commit_data.get('timestamp', 0)
        if timestamp == 0:
            timestamp = int(time.time())
        
        dt = datetime.datetime.fromtimestamp(timestamp)
        tz_offset = time.strftime("%z")
        if not tz_offset:
            tz_offset = "+0000"
        
        formatted_date = dt.strftime("%a %b %d %H:%M:%S %Y ") + tz_offset
        print(f"Date:   {formatted_date}")
        print()
        
        # Show commit message
        for line in commit_data['message'].split('\\n'):
            print(f"    {line}")
        print()
        
        # Show file changes if requested
        if name_status or name_only or stat or not no_patch:
            self._show_commit_changes(commit_data, name_status, name_only, stat, no_patch)
    
    def _show_commit_changes(self, commit_data: dict, name_status: bool, 
                           name_only: bool, stat: bool, no_patch: bool):
        """Show changes in a commit."""
        tree_hash = commit_data['tree']
        parent_hash = commit_data.get('parent')
        
        # Get current tree files
        current_files = self.repo._read_tree(tree_hash)
        
        # Get parent tree files
        parent_files = {}
        if parent_hash:
            try:
                parent_obj_type, parent_content = self.repo._read_object(parent_hash)
                if parent_obj_type == "commit":
                    parent_commit_data = json.loads(parent_content.decode())
                    parent_tree_hash = parent_commit_data['tree']
                    parent_files = self.repo._read_tree(parent_tree_hash)
            except Exception:
                pass
        
        # Calculate changes
        added_files = []
        modified_files = []
        deleted_files = []
        
        # Find added and modified files
        for file_path, file_hash in current_files.items():
            if file_path not in parent_files:
                added_files.append(file_path)
            elif parent_files[file_path] != file_hash:
                modified_files.append(file_path)
        
        # Find deleted files
        for file_path in parent_files.keys():
            if file_path not in current_files:
                deleted_files.append(file_path)
        
        # Show output based on options
        if name_status:
            for file_path in added_files:
                print(f"A\\t{file_path}")
            for file_path in modified_files:
                print(f"M\\t{file_path}")
            for file_path in deleted_files:
                print(f"D\\t{file_path}")
        elif name_only:
            for file_path in sorted(added_files + modified_files + deleted_files):
                print(file_path)
        elif stat:
            total_files = len(added_files) + len(modified_files) + len(deleted_files)
            if total_files > 0:
                print(f" {total_files} file{'s' if total_files != 1 else ''} changed")
                for file_path in added_files:
                    print(f" create mode 100644 {file_path}")
                for file_path in deleted_files:
                    print(f" delete mode 100644 {file_path}")
        elif not no_patch:
            # Show basic diff info (simplified)
            if added_files or modified_files or deleted_files:
                for file_path in added_files:
                    print(f"new file mode 100644")
                    print(f"index 0000000..{current_files[file_path][:7]} 100644")
                    print(f"--- /dev/null")
                    print(f"+++ b/{file_path}")
                    print("@@ -0,0 +1,1 @@")
                    print("+[file content]")
                    print()
                
                for file_path in modified_files:
                    print(f"index {parent_files[file_path][:7]}..{current_files[file_path][:7]} 100644")
                    print(f"--- a/{file_path}")
                    print(f"+++ b/{file_path}")
                    print("@@ -1,1 +1,1 @@")
                    print("-[old content]")
                    print("+[new content]")
                    print()
                
                for file_path in deleted_files:
                    print(f"deleted file mode 100644")
                    print(f"index {parent_files[file_path][:7]}..0000000 100644")
                    print(f"--- a/{file_path}")
                    print(f"+++ /dev/null")
                    print("@@ -1,1 +0,0 @@")
                    print("-[file content]")
                    print()
    
    def _show_tree(self, tree_hash: str, content: bytes):
        """Show a tree object."""
        print(f"tree {tree_hash}")
        print()
        
        if content:
            for line in content.decode().split('\\n'):
                if line.strip():
                    parts = line.split(' ', 2)
                    if len(parts) == 3:
                        obj_type, obj_hash, filename = parts
                        print(f"{obj_type} {obj_hash} {filename}")
    
    def _show_blob(self, blob_hash: str, content: bytes):
        """Show a blob object."""
        print(f"blob {blob_hash}")
        print()
        try:
            # Try to decode as text
            text_content = content.decode('utf-8')
            print(text_content)
        except UnicodeDecodeError:
            # Binary file
            print(f"Binary file ({len(content)} bytes)")
    
    def _resolve_object(self, object_ref: str) -> str:
        """Resolve object reference to hash."""
        if object_ref == 'HEAD':
            current_branch = self.repo._get_current_branch()
            commit_hash = self.repo._get_branch_commit(current_branch)
            if not commit_hash:
                raise RVSError("HEAD does not point to a valid commit")
            return commit_hash
        
        # Try as branch name
        branch_commit = self.repo._get_branch_commit(object_ref)
        if branch_commit:
            return branch_commit
        
        # Try as full hash
        try:
            obj_type, content = self.repo._read_object(object_ref)
            return object_ref
        except Exception:
            pass
        
        # Try partial hash matching
        if len(object_ref) >= 4:
            for obj_dir in self.repo.objects_dir.iterdir():
                if obj_dir.is_dir() and len(obj_dir.name) == 2:
                    for obj_file in obj_dir.iterdir():
                        full_hash = obj_dir.name + obj_file.name
                        if full_hash.startswith(object_ref):
                            try:
                                obj_type, content = self.repo._read_object(full_hash)
                                return full_hash
                            except Exception:
                                continue
        
        raise RVSError(f"Not a valid object: {object_ref}")
    
    def execute(self):
        """Legacy execute method."""
        self.show_object('HEAD')