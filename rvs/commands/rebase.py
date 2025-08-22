"""Rebase command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List, Optional
from .base import BaseCommand
from ..exceptions import RVSError

class RebaseCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('rebase', help='Reapply commits on top of another base tip')
        parser.add_argument('upstream', nargs='?', help='Upstream branch or commit')
        parser.add_argument('branch', nargs='?', help='Working branch (default: current)')
        parser.add_argument('-i', '--interactive', action='store_true',
                          help='Make a list of the commits which are about to be rebased')
        parser.add_argument('--continue', action='store_true',
                          help='Continue the rebase after resolving conflicts')
        parser.add_argument('--abort', action='store_true',
                          help='Abort the rebase operation')
        parser.add_argument('--skip', action='store_true',
                          help='Skip the current patch')
        parser.add_argument('--onto', 
                          help='Starting point at which to create the new commits')
        parser.add_argument('-f', '--force-rebase', action='store_true',
                          help='Force rebase even if branch is up to date')
        parser.add_argument('--root', action='store_true',
                          help='Rebase all commits reachable from branch')
        return parser
    
    def execute_from_args(self, args: Any):
        if args.abort:
            self.abort_rebase()
        elif getattr(args, 'continue', False):  # 'continue' is a keyword
            self.continue_rebase()
        elif args.skip:
            self.skip_rebase()
        elif args.upstream:
            self.rebase(
                upstream=args.upstream,
                branch=args.branch,
                interactive=args.interactive,
                onto=args.onto,
                force=args.force_rebase,
                root=args.root
            )
        else:
            print("Usage: rvs rebase <upstream> [<branch>]")
    
    def rebase(self, upstream: str, branch: Optional[str] = None,
               interactive: bool = False, onto: Optional[str] = None,
               force: bool = False, root: bool = False):
        """Rebase current branch onto upstream."""
        self.repo._ensure_repo_exists()
        
        # Get current branch if not specified
        if not branch:
            branch = self.repo._get_current_branch()
        
        # Get current commit
        current_commit = self.repo._get_branch_commit(branch)
        if not current_commit:
            raise RVSError(f"Branch {branch} has no commits")
        
        # Resolve upstream
        upstream_commit = self._resolve_commit(upstream)
        
        # Check if already up to date
        if current_commit == upstream_commit and not force:
            print("Current branch is up to date.")
            return
        
        # Get commits to rebase
        commits_to_rebase = self._get_commits_to_rebase(current_commit, upstream_commit)
        
        if not commits_to_rebase and not force:
            print("Current branch is up to date.")
            return
        
        print(f"Rebasing {len(commits_to_rebase)} commits onto {upstream}")
        
        if interactive:
            self._interactive_rebase(commits_to_rebase, upstream_commit, branch)
        else:
            self._linear_rebase(commits_to_rebase, upstream_commit, branch)
    
    def _linear_rebase(self, commits: List[str], new_base: str, branch: str):
        """Perform a linear rebase."""
        current_base = new_base
        
        for i, commit_hash in enumerate(commits):
            print(f"Applying commit {i+1}/{len(commits)}: {commit_hash[:8]}")
            
            try:
                # Get commit info
                commit_data = self._get_commit_data(commit_hash)
                
                # Get commit files
                commit_files = self._get_commit_files(commit_hash)
                
                # Create new commit on top of current base
                new_commit = self._create_commit_on_base(
                    commit_files, commit_data['message'], current_base
                )
                
                current_base = new_commit
                print(f"  -> {new_commit[:8]}")
                
            except Exception as e:
                print(f"Failed to apply commit {commit_hash[:8]}: {e}")
                print("Resolve conflicts and run 'rvs rebase --continue'")
                return
        
        # Update branch to point to new head
        self.repo._set_branch_commit(branch, current_base)
        
        # Update working tree
        self._update_working_tree(current_base)
        
        print(f"Successfully rebased {branch} onto {new_base[:8]}")
    
    def _interactive_rebase(self, commits: List[str], new_base: str, branch: str):
        """Perform an interactive rebase."""
        print("Interactive rebase not fully implemented yet.")
        print("Available commits to rebase:")
        
        for i, commit_hash in enumerate(commits):
            commit_data = self._get_commit_data(commit_hash)
            message = commit_data['message'].split('\n')[0]  # First line only
            print(f"pick {commit_hash[:8]} {message}")
        
        print("\nWould perform linear rebase...")
        self._linear_rebase(commits, new_base, branch)
    
    def _get_commits_to_rebase(self, current: str, upstream: str) -> List[str]:
        """Get list of commits that need to be rebased."""
        commits = []
        
        # Walk back from current commit until we reach upstream or a common ancestor
        # This is a simplified implementation
        commit_hash = current
        visited = set()
        
        while commit_hash and commit_hash != upstream and commit_hash not in visited:
            visited.add(commit_hash)
            commits.append(commit_hash)
            
            # Get parent commit
            try:
                commit_data = self._get_commit_data(commit_hash)
                commit_hash = commit_data.get('parent')
            except Exception:
                break
        
        # Reverse to get chronological order
        return list(reversed(commits))
    
    def _get_commit_data(self, commit_hash: str) -> dict:
        """Get commit data."""
        obj_type, content = self.repo._read_object(commit_hash)
        if obj_type != "commit":
            raise RVSError(f"Not a commit: {commit_hash}")
        
        import json
        return json.loads(content.decode())
    
    def _get_commit_files(self, commit_hash: str) -> dict:
        """Get files from commit."""
        commit_data = self._get_commit_data(commit_hash)
        tree_hash = commit_data['tree']
        return self.repo._read_tree(tree_hash)
    
    def _create_commit_on_base(self, files: dict, message: str, parent: str) -> str:
        """Create a new commit with given files and parent."""
        import json
        import time
        from datetime import datetime
        
        # Create tree
        tree_hash = self.repo._create_tree(files)
        
        # Create commit
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
        return self.repo._write_object(commit_content, "commit")
    
    def _update_working_tree(self, commit_hash: str):
        """Update working tree to match commit."""
        files = self._get_commit_files(commit_hash)
        
        # Clear working tree first
        self._clear_working_tree()
        
        # Restore files
        for file_path, file_hash in files.items():
            self._restore_file_from_hash(file_path, file_hash)
    
    def _clear_working_tree(self):
        """Clear working tree of tracked files."""
        # Get current index to know which files to remove
        index = self.repo._load_index()
        
        for file_path in index.keys():
            full_path = self.repo.repo_path / file_path
            if full_path.exists():
                try:
                    full_path.unlink()
                except Exception:
                    pass
    
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
    
    def abort_rebase(self):
        """Abort current rebase."""
        print("Rebase abort not implemented yet")
        print("You can manually reset your branch to the original state")
    
    def continue_rebase(self):
        """Continue current rebase."""
        print("Rebase continue not implemented yet")
        print("Resolve conflicts manually and commit, then run rebase again")
    
    def skip_rebase(self):
        """Skip current rebase step."""
        print("Rebase skip not implemented yet")
    
    def execute(self):
        """Legacy execute method."""
        print('Rebase command executed')
