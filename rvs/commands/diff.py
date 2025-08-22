"""
Diff command implementation.
"""
import difflib
import os
from argparse import ArgumentParser, _SubParsersAction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseCommand

class DiffCommand(BaseCommand):
    """Show changes between commits, commit and working tree, etc."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register diff command parser."""
        parser = subparsers.add_parser(
            "diff",
            help="Show changes between commits, commit and working tree, etc"
        )
        parser.add_argument(
            "--cached", "--staged",
            action="store_true",
            dest="cached",
            help="Show changes between index and HEAD"
        )
        parser.add_argument(
            "--name-only",
            action="store_true",
            help="Show only names of changed files"
        )
        parser.add_argument(
            "--name-status",
            action="store_true",
            help="Show only names and status of changed files"
        )
        parser.add_argument(
            "commits",
            nargs="*",
            help="Commit(s) to compare (0, 1, or 2 commits)"
        )
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute diff command from parsed arguments."""
        self.execute(
            cached=args.cached,
            name_only=args.name_only,
            name_status=args.name_status,
            commits=args.commits
        )
    
    def execute(self, cached: bool = False, name_only: bool = False, 
                name_status: bool = False, commits: List[str] = None) -> None:
        """Show differences between various states."""
        self.repo._ensure_repo_exists()
        
        commits = commits or []
        
        if len(commits) > 2:
            print("fatal: too many arguments")
            return
        
        if cached:
            # Show changes between index and HEAD
            self._diff_index_head(name_only, name_status)
        elif len(commits) == 0:
            # Show changes between working directory and index
            self._diff_working_index(name_only, name_status)
        elif len(commits) == 1:
            # Show changes between working directory and specified commit
            self._diff_working_commit(commits[0], name_only, name_status)
        elif len(commits) == 2:
            # Show changes between two commits
            self._diff_commit_commit(commits[0], commits[1], name_only, name_status)
    
    def _diff_index_head(self, name_only: bool, name_status: bool) -> None:
        """Show changes between index (staged files) and HEAD."""
        # Get HEAD commit files
        current_branch = self.repo._get_current_branch()
        head_commit = self.repo._get_branch_commit(current_branch)
        
        head_files = {}
        if head_commit:
            try:
                commit_data = self.repo._read_commit(head_commit)
                tree_hash = commit_data['tree']
                head_files = self.repo._read_tree(tree_hash)
            except Exception:
                pass  # No HEAD or error reading
        
        # Get index files
        index_files = self.repo._load_index()
        
        # Find differences
        self._show_diff(head_files, index_files, "HEAD", "index", name_only, name_status)
    
    def _diff_working_index(self, name_only: bool, name_status: bool) -> None:
        """Show changes between working directory and index."""
        # Get index files
        index_files = self.repo._load_index()
        
        # Get working directory files
        working_files = self._get_working_files()
        
        # Find differences
        self._show_diff(index_files, working_files, "index", "working tree", name_only, name_status)
    
    def _diff_working_commit(self, commit_ref: str, name_only: bool, name_status: bool) -> None:
        """Show changes between working directory and a specific commit."""
        # Resolve commit reference
        commit_hash = self._resolve_commit_ref(commit_ref)
        if not commit_hash:
            print(f"fatal: bad revision '{commit_ref}'")
            return
        
        # Get commit files
        try:
            commit_data = self.repo._read_commit(commit_hash)
            tree_hash = commit_data['tree']
            commit_files = self.repo._read_tree(tree_hash)
        except Exception as e:
            print(f"fatal: error reading commit {commit_ref}: {e}")
            return
        
        # Get working directory files
        working_files = self._get_working_files()
        
        # Find differences
        self._show_diff(commit_files, working_files, commit_ref, "working tree", name_only, name_status)
    
    def _diff_commit_commit(self, commit1_ref: str, commit2_ref: str, name_only: bool, name_status: bool) -> None:
        """Show changes between two commits."""
        # Resolve commit references
        commit1_hash = self._resolve_commit_ref(commit1_ref)
        commit2_hash = self._resolve_commit_ref(commit2_ref)
        
        if not commit1_hash:
            print(f"fatal: bad revision '{commit1_ref}'")
            return
        if not commit2_hash:
            print(f"fatal: bad revision '{commit2_ref}'")
            return
        
        # Get files from both commits
        try:
            commit1_data = self.repo._read_commit(commit1_hash)
            tree1_hash = commit1_data['tree']
            commit1_files = self.repo._read_tree(tree1_hash)
            
            commit2_data = self.repo._read_commit(commit2_hash)
            tree2_hash = commit2_data['tree']
            commit2_files = self.repo._read_tree(tree2_hash)
        except Exception as e:
            print(f"fatal: error reading commits: {e}")
            return
        
        # Find differences
        self._show_diff(commit1_files, commit2_files, commit1_ref, commit2_ref, name_only, name_status)
    
    def _resolve_commit_ref(self, ref: str) -> Optional[str]:
        """Resolve a commit reference (HEAD, branch name, or commit hash)."""
        if ref == "HEAD":
            current_branch = self.repo._get_current_branch()
            return self.repo._get_branch_commit(current_branch)
        
        # Try as branch name
        branch_commit = self.repo._get_branch_commit(ref)
        if branch_commit:
            return branch_commit
        
        # Try as commit hash (full or partial)
        if len(ref) >= 4:  # Minimum hash length
            # Search for matching commit hash
            for obj_dir in self.repo.objects_dir.iterdir():
                if obj_dir.is_dir() and len(obj_dir.name) == 2:
                    for obj_file in obj_dir.iterdir():
                        full_hash = obj_dir.name + obj_file.name
                        if full_hash.startswith(ref):
                            # Verify it's a commit object
                            try:
                                obj_type, _ = self.repo._read_object(full_hash)
                                if obj_type == "commit":
                                    return full_hash
                            except:
                                continue
        
        return None
    
    def _get_working_files(self) -> Dict[str, str]:
        """Get all files in working directory with their hashes."""
        working_files = {}
        for file_path in self.repo.repo_path.rglob('*'):
            if file_path.is_file() and not str(file_path).startswith(str(self.repo.rvs_dir)):
                rel_path = file_path.relative_to(self.repo.repo_path)
                try:
                    working_files[str(rel_path)] = self.repo._get_file_hash(file_path)
                except Exception:
                    # Skip files that can't be read
                    pass
        return working_files
    
    def _show_diff(self, old_files: Dict[str, str], new_files: Dict[str, str], 
                   old_label: str, new_label: str, name_only: bool, name_status: bool) -> None:
        """Show differences between two file sets."""
        all_files = set(old_files.keys()) | set(new_files.keys())
        
        if not all_files:
            return
        
        changed_files = []
        
        for file_path in sorted(all_files):
            old_hash = old_files.get(file_path)
            new_hash = new_files.get(file_path)
            
            if old_hash != new_hash:
                if old_hash is None:
                    # New file
                    status = "A"
                elif new_hash is None:
                    # Deleted file
                    status = "D"
                else:
                    # Modified file
                    status = "M"
                
                changed_files.append((status, file_path, old_hash, new_hash))
        
        if not changed_files:
            return
        
        if name_only:
            # Show only file names
            for _, file_path, _, _ in changed_files:
                print(file_path)
        elif name_status:
            # Show status and file names
            for status, file_path, _, _ in changed_files:
                print(f"{status}\t{file_path}")
        else:
            # Show full diff
            for status, file_path, old_hash, new_hash in changed_files:
                self._show_file_diff(file_path, old_hash, new_hash, old_label, new_label)
    
    def _show_file_diff(self, file_path: str, old_hash: Optional[str], 
                        new_hash: Optional[str], old_label: str, new_label: str) -> None:
        """Show diff for a single file."""
        # Get file contents
        old_content = ""
        new_content = ""
        
        if old_hash:
            try:
                obj_type, content_bytes = self.repo._read_object(old_hash)
                if obj_type == "blob":
                    old_content = content_bytes.decode('utf-8', errors='replace')
            except Exception:
                old_content = "<binary file>"
        
        if new_hash:
            try:
                obj_type, content_bytes = self.repo._read_object(new_hash)
                if obj_type == "blob":
                    new_content = content_bytes.decode('utf-8', errors='replace')
            except Exception:
                # Try reading from working directory
                try:
                    file_full_path = self.repo.repo_path / file_path
                    if file_full_path.exists():
                        with open(file_full_path, 'r', encoding='utf-8', errors='replace') as f:
                            new_content = f.read()
                except Exception:
                    new_content = "<binary file>"
        
        # Check if files are binary
        if "<binary file>" in [old_content, new_content] or self._is_binary(old_content) or self._is_binary(new_content):
            print(f"diff --git a/{file_path} b/{file_path}")
            if old_hash is None:
                print("new file mode 100644")
                print(f"index 0000000..{new_hash[:7]}")
            elif new_hash is None:
                print("deleted file mode 100644")
                print(f"index {old_hash[:7]}..0000000")
            else:
                print(f"index {old_hash[:7]}..{new_hash[:7]} 100644")
            print("Binary files differ")
            return
        
        # Generate unified diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Create diff using Python's difflib (which matches Git's format closely)
        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        ))
        
        if not diff_lines:
            return
        
        # Print Git-style header
        print(f"diff --git a/{file_path} b/{file_path}")
        
        if old_hash is None:
            print("new file mode 100644")
            print(f"index 0000000..{new_hash[:7]}")
        elif new_hash is None:
            print("deleted file mode 100644")
            print(f"index {old_hash[:7]}..0000000")
        else:
            print(f"index {old_hash[:7]}..{new_hash[:7]} 100644")
        
        # Print diff content
        for line in diff_lines:
            print(line)
    
    def _is_binary(self, content: str) -> bool:
        """Check if content appears to be binary."""
        if not content:
            return False
        
        # Simple heuristic: if content contains null bytes or too many non-printable chars
        null_count = content.count('\0')
        if null_count > 0:
            return True
        
        # Check for high ratio of non-printable characters
        printable_chars = sum(1 for c in content if c.isprintable() or c in '\n\r\t')
        total_chars = len(content)
        
        if total_chars > 0 and printable_chars / total_chars < 0.75:
            return True
        
        return False