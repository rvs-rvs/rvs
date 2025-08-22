"""Merge command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class MergeCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('merge', help='Join two or more development histories together')
        parser.add_argument('commit', nargs='*', help='Commits to merge')
        parser.add_argument('-m', '--message', 
                          help='Set the commit message to be used for the merge commit')
        parser.add_argument('--no-commit', action='store_true',
                          help='Perform the merge but pretend the merge failed')
        parser.add_argument('--no-ff', action='store_true',
                          help='Create a merge commit even when the merge resolves as a fast-forward')
        parser.add_argument('--ff-only', action='store_true',
                          help='Refuse to merge and exit unless the current HEAD is already up to date')
        parser.add_argument('--abort', action='store_true',
                          help='Abort the current conflict resolution process')
        parser.add_argument('--continue', action='store_true',
                          help='Continue the current conflict resolution process')
        parser.add_argument('-s', '--strategy', 
                          help='Use the given merge strategy')
        parser.add_argument('--squash', action='store_true',
                          help='Create a single commit instead of doing a merge')
        return parser
    
    def execute_from_args(self, args: Any):
        if args.abort:
            self.abort_merge()
        elif getattr(args, 'continue', False):  # 'continue' is a keyword
            self.continue_merge()
        elif args.commit:
            self.merge(
                commits=args.commit,
                message=args.message,
                no_commit=args.no_commit,
                no_ff=args.no_ff,
                ff_only=args.ff_only,
                squash=args.squash
            )
        else:
            print("Nothing to merge")
    
    def merge(self, commits: List[str], message: Optional[str] = None,
              no_commit: bool = False, no_ff: bool = False, ff_only: bool = False,
              squash: bool = False):
        """Merge one or more commits into current branch."""
        self.repo._ensure_repo_exists()
        
        if len(commits) != 1:
            raise RVSError("Multi-way merge not implemented yet")
        
        target_commit = commits[0]
        
        # Get current branch and commit
        current_branch = self.repo._get_current_branch()
        current_commit = self.repo._get_branch_commit(current_branch)
        
        if not current_commit:
            raise RVSError("Cannot merge: no commits on current branch")
        
        # Resolve target commit
        target_hash = self._resolve_commit(target_commit)
        
        if current_commit == target_hash:
            print("Already up to date.")
            return
        
        # Check if it's a fast-forward merge
        is_fast_forward = self._is_fast_forward(current_commit, target_hash)
        
        if ff_only and not is_fast_forward:
            raise RVSError("Not possible to fast-forward, exiting.")
        
        if is_fast_forward and not no_ff:
            # Fast-forward merge
            self._fast_forward_merge(current_branch, target_hash, target_commit)
        else:
            # Three-way merge
            self._three_way_merge(
                current_commit, target_hash, target_commit,
                current_branch, message, no_commit, squash
            )
    
    def _fast_forward_merge(self, branch: str, target_hash: str, target_name: str):
        """Perform a fast-forward merge."""
        # Update branch pointer
        self.repo._set_branch_commit(branch, target_hash)
        
        # Update working tree
        self._update_working_tree(target_hash)
        
        print(f"Fast-forward merge from {target_name}")
        print(f"Updated {branch} to {target_hash[:8]}")
    
    def _three_way_merge(self, current_commit: str, target_commit: str, target_name: str,
                        branch: str, message: Optional[str], no_commit: bool, squash: bool):
        """Perform a three-way merge."""
        # Find merge base (simplified - find common ancestor)
        merge_base = self._find_merge_base(current_commit, target_commit)
        
        # Get file trees
        current_files = self._get_commit_files(current_commit)
        target_files = self._get_commit_files(target_commit)
        base_files = self._get_commit_files(merge_base)
        
        # Perform merge
        merged_files, conflicts = self._merge_trees(base_files, current_files, target_files)
        
        if conflicts:
            self._handle_conflicts(conflicts)
            print("Automatic merge failed; fix conflicts and then commit the result.")
            return
        
        # Update working tree with merged files
        self._apply_merged_files(merged_files)
        
        if no_commit:
            print("Merge completed but not committed (--no-commit)")
            return
        
        # Create merge commit
        if not message:
            message = f"Merge {target_name} into {branch}"
        
        if squash:
            # Squash merge - don't record merge parent
            self._create_commit(merged_files, message, current_commit)
            print(f"Squash merge from {target_name}")
        else:
            # Regular merge commit with two parents
            self._create_merge_commit(merged_files, message, current_commit, target_commit)
            print(f"Merge made by the 'recursive' strategy.")
    
    def _merge_trees(self, base_files: Dict[str, str], current_files: Dict[str, str], 
                    target_files: Dict[str, str]) -> Tuple[Dict[str, str], List[str]]:
        """Merge three file trees with improved conflict handling."""
        merged_files = {}
        conflicts = []
        
        # Get all file paths
        all_files = set(base_files.keys()) | set(current_files.keys()) | set(target_files.keys())
        
        for file_path in all_files:
            base_hash = base_files.get(file_path)
            current_hash = current_files.get(file_path)
            target_hash = target_files.get(file_path)
            
            # Determine merge result
            if current_hash == target_hash:
                # Same in both branches
                if current_hash:
                    merged_files[file_path] = current_hash
            elif current_hash == base_hash:
                # Only changed in target branch
                if target_hash:
                    merged_files[file_path] = target_hash
            elif target_hash == base_hash:
                # Only changed in current branch
                if current_hash:
                    merged_files[file_path] = current_hash
            else:
                # Changed in both branches - this is a conflict
                conflicts.append(file_path)
                # Create conflict markers and write to working directory
                conflict_content = self._create_conflict_markers(
                    base_hash, current_hash, target_hash
                )
                if conflict_content:
                    # Write conflict markers to working directory
                    self._write_conflict_file(file_path, conflict_content)
                # Keep current version in merged_files for now
                if current_hash:
                    merged_files[file_path] = current_hash
        
        return merged_files, conflicts
    
    def _three_way_merge_content(self, base_hash: str, current_hash: str, target_hash: str) -> Optional[bytes]:
        """Attempt a three-way merge of file contents."""
        # Get file contents
        base_content = self._get_blob_content(base_hash) if base_hash else b""
        current_content = self._get_blob_content(current_hash) if current_hash else b""
        target_content = self._get_blob_content(target_hash) if target_hash else b""
        
        # If all versions are identical, no merge needed
        if current_content == target_content:
            return current_content
        
        # If one side is unchanged, use the other side
        if current_content == base_content:
            return target_content
        if target_content == base_content:
            return current_content
        
        # Both sides changed - this is a conflict
        # Create conflict markers
        merged_lines = [
            b"<<<<<<< HEAD\n",
            current_content,
            b"\n=======\n",
            target_content,
            b"\n>>>>>>> target\n"
        ]
        
        # Return None to indicate conflict (caller should handle this)
        return None
    
    def _create_conflict_markers(self, base_hash: str, current_hash: str, target_hash: str) -> bytes:
        """Create conflict markers for a file."""
        current_content = self._get_blob_content(current_hash) if current_hash else b""
        target_content = self._get_blob_content(target_hash) if target_hash else b""
        
        conflict_content = (
            b"<<<<<<< HEAD\n" +
            current_content +
            (b"\n" if current_content and not current_content.endswith(b"\n") else b"") +
            b"=======\n" +
            target_content +
            (b"\n" if target_content and not target_content.endswith(b"\n") else b"") +
            b">>>>>>> target\n"
        )
        
        return conflict_content
    
    def _write_conflict_file(self, file_path: str, content: bytes):
        """Write conflict content to working directory file."""
        full_path = self.repo.repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(content)
    
    def _get_blob_content(self, blob_hash: str) -> bytes:
        """Get content of a blob object."""
        try:
            obj_type, content = self.repo._read_object(blob_hash)
            if obj_type != "blob":
                return b""
            return content
        except Exception:
            return b""
    
    def _apply_merged_files(self, merged_files: Dict[str, str]):
        """Apply merged files to working tree and index."""
        # Update working tree
        for file_path, file_hash in merged_files.items():
            self._restore_file_from_hash(file_path, file_hash)
        
        # Update index
        self.repo._save_index(merged_files)
    
    def _create_merge_commit(self, files: Dict[str, str], message: str, 
                           parent1: str, parent2: str):
        """Create a merge commit with two parents."""
        import json
        import time
        from datetime import datetime
        
        # Create tree
        tree_hash = self.repo._create_tree(files)
        
        # Create merge commit
        timestamp = int(time.time())
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        commit_data = {
            "tree": tree_hash,
            "parents": [parent1, parent2],
            "message": message,
            "timestamp": timestamp,
            "date": date_str,
            "author": "RVS User"
        }
        
        commit_content = json.dumps(commit_data, indent=2).encode()
        commit_hash = self.repo._write_object(commit_content, "commit")
        
        # Update branch
        current_branch = self.repo._get_current_branch()
        self.repo._set_branch_commit(current_branch, commit_hash)
        
        print(f"Created merge commit {commit_hash[:8]}")
    
    def _create_commit(self, files: Dict[str, str], message: str, parent: str):
        """Create a regular commit."""
        import json
        import time
        from datetime import datetime
        
        tree_hash = self.repo._create_tree(files)
        
        timestamp = int(time.time())
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        commit_data = {
            "tree": tree_hash,
            "parent": parent,
            "message": message,
            "timestamp": timestamp,
            "date": date_str,
            "author": "RVS User"
        }
        
        commit_content = json.dumps(commit_data, indent=2).encode()
        commit_hash = self.repo._write_object(commit_content, "commit")
        
        current_branch = self.repo._get_current_branch()
        self.repo._set_branch_commit(current_branch, commit_hash)
        
        print(f"Created commit {commit_hash[:8]}")
    
    def _handle_conflicts(self, conflicts: List[str]):
        """Handle merge conflicts."""
        print("CONFLICT (content): Merge conflict in the following files:")
        for file_path in conflicts:
            print(f"\t{file_path}")
    
    def _get_commit_files(self, commit_hash: str) -> Dict[str, str]:
        """Get files from a commit."""
        try:
            obj_type, content = self.repo._read_object(commit_hash)
            if obj_type != "commit":
                return {}
            
            import json
            commit_data = json.loads(content.decode())
            tree_hash = commit_data['tree']
            return self.repo._read_tree(tree_hash)
        except Exception:
            return {}
    
    def _update_working_tree(self, commit_hash: str):
        """Update working tree to match commit."""
        files = self._get_commit_files(commit_hash)
        for file_path, file_hash in files.items():
            self._restore_file_from_hash(file_path, file_hash)
    
    def _restore_file_from_hash(self, file_path: str, file_hash: str):
        """Restore file from hash."""
        try:
            obj_type, content = self.repo._read_object(file_hash)
            if obj_type != "blob":
                return
            
            full_path = self.repo.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(content)
        except Exception:
            pass
    
    def _resolve_commit(self, commit_ish: str) -> str:
        """Resolve commit-ish to commit hash."""
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
    
    def _find_merge_base(self, commit1: str, commit2: str) -> str:
        """Find the merge base (common ancestor) of two commits."""
        # Simplified implementation - walk back from commit1 to find common ancestor
        # In a real implementation, this would use a more sophisticated algorithm
        
        # Get all ancestors of commit2
        commit2_ancestors = set()
        current = commit2
        while current:
            commit2_ancestors.add(current)
            try:
                commit_data = self._get_commit_data(current)
                current = commit_data.get('parent')
            except Exception:
                break
        
        # Walk back from commit1 until we find a common ancestor
        current = commit1
        while current:
            if current in commit2_ancestors:
                return current
            try:
                commit_data = self._get_commit_data(current)
                current = commit_data.get('parent')
            except Exception:
                break
        
        # If no common ancestor found, use commit1 as base (fallback)
        return commit1
    
    def _get_commit_data(self, commit_hash: str) -> dict:
        """Get commit data."""
        obj_type, content = self.repo._read_object(commit_hash)
        if obj_type != "commit":
            raise RVSError(f"Not a commit: {commit_hash}")
        
        import json
        return json.loads(content.decode())
    
    def _is_fast_forward(self, current: str, target: str) -> bool:
        """Check if target is ahead of current (fast-forward possible)."""
        # Simplified check - in a real implementation, we'd walk the commit graph
        # For now, assume it's not a fast-forward if they're different
        return False
    
    def abort_merge(self):
        """Abort current merge."""
        print("Merge abort not implemented yet")
    
    def continue_merge(self):
        """Continue current merge."""
        print("Merge continue not implemented yet")
    
    def execute(self):
        """Legacy execute method."""
        print('Merge command executed')
