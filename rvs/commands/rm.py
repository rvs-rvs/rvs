"""Remove command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class RmCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('rm', help='Remove files from the working tree and from the index')
        parser.add_argument('pathspec', nargs='+', help='Files to remove')
        parser.add_argument('-f', '--force', action='store_true',
                          help='Override the up-to-date check')
        parser.add_argument('-n', '--dry-run', action='store_true',
                          help='Don\'t actually remove any file(s)')
        parser.add_argument('-r', '--recursive', action='store_true',
                          help='Allow recursive removal when a leading directory name is given')
        parser.add_argument('--cached', action='store_true',
                          help='Only remove from the index')
        parser.add_argument('--ignore-unmatch', action='store_true',
                          help='Exit with a zero status even if nothing matched')
        parser.add_argument('-q', '--quiet', action='store_true',
                          help='Quiet mode')
        return parser
    
    def execute_from_args(self, args: Any):
        self.remove(
            pathspec=args.pathspec,
            force=args.force,
            dry_run=args.dry_run,
            recursive=args.recursive,
            cached=args.cached,
            ignore_unmatch=args.ignore_unmatch,
            quiet=args.quiet
        )
    
    def remove(self, pathspec: List[str], force: bool = False, dry_run: bool = False,
               recursive: bool = False, cached: bool = False, 
               ignore_unmatch: bool = False, quiet: bool = False):
        """Remove files from working tree and/or index."""
        self.repo._ensure_repo_exists()
        
        # Load current index
        index = self.repo._load_index()
        
        # Get current commit files for comparison
        committed_files = {}
        current_branch = self.repo._get_current_branch()
        commit_hash = self.repo._get_branch_commit(current_branch)
        if commit_hash:
            try:
                obj_type, content = self.repo._read_object(commit_hash)
                if obj_type == "commit":
                    import json
                    commit_data = json.loads(content.decode())
                    tree_hash = commit_data['tree']
                    committed_files = self.repo._read_tree(tree_hash)
            except Exception:
                pass
        
        removed_files = []
        errors = []
        
        for pattern in pathspec:
            matched_files = self._match_pathspec(pattern, index, committed_files, recursive)
            
            if not matched_files and not ignore_unmatch:
                errors.append(f"pathspec '{pattern}' did not match any files")
                continue
            
            for file_path in matched_files:
                try:
                    self._remove_file(
                        file_path, index, committed_files, 
                        force, dry_run, cached, quiet
                    )
                    removed_files.append(file_path)
                except RVSError as e:
                    errors.append(str(e))
        
        # Save updated index if not dry run
        if not dry_run and removed_files:
            self.repo._save_index(index)
        
        # Report results
        if not quiet:
            for file_path in removed_files:
                if dry_run:
                    print(f"rm '{file_path}'")
                else:
                    print(f"rm '{file_path}'")
        
        # Report errors
        if errors and not ignore_unmatch:
            for error in errors:
                print(f"fatal: {error}")
            if not dry_run:
                raise RVSError("Some files could not be removed")
    
    def _match_pathspec(self, pattern: str, index: dict, committed_files: dict, recursive: bool) -> List[str]:
        """Match pathspec pattern against index and committed files."""
        matched = []
        
        # Check both index and committed files
        all_tracked_files = set(index.keys()) | set(committed_files.keys())
        
        if pattern in all_tracked_files:
            # Exact match
            matched.append(pattern)
        else:
            # Check if it's a directory pattern
            pattern_path = Path(pattern)
            
            for file_path in all_tracked_files:
                file_path_obj = Path(file_path)
                
                # Check if file is under the pattern directory
                try:
                    file_path_obj.relative_to(pattern_path)
                    if recursive or len(file_path_obj.parts) == len(pattern_path.parts) + 1:
                        matched.append(file_path)
                except ValueError:
                    # Not under the pattern directory
                    continue
        
        return matched
    
    def _remove_file(self, file_path: str, index: dict, committed_files: dict,
                     force: bool, dry_run: bool, cached: bool, quiet: bool):
        """Remove a single file."""
        full_path = self.repo.repo_path / file_path
        
        # Check if file is tracked (in index or committed)
        if file_path not in index and file_path not in committed_files:
            raise RVSError(f"'{file_path}' is not tracked by rvs")
        
        # Safety checks (unless forced)
        if not force:
            # Check if file has uncommitted changes
            if full_path.exists():
                current_hash = self.repo._get_file_hash(full_path)
                staged_hash = index.get(file_path, committed_files.get(file_path))
                
                if current_hash != staged_hash:
                    raise RVSError(f"'{file_path}' has local modifications")
                
                # Check if staged differs from committed
                if file_path in committed_files:
                    committed_hash = committed_files[file_path]
                    if staged_hash != committed_hash:
                        raise RVSError(f"'{file_path}' has changes staged in the index")
        
        if not dry_run:
            # Remove from index (this stages the deletion)
            if file_path in index:
                del index[file_path]
            
            # Remove from working tree (unless --cached)
            if not cached and full_path.exists():
                try:
                    full_path.unlink()
                    
                    # Remove empty parent directories
                    parent = full_path.parent
                    while parent != self.repo.repo_path:
                        try:
                            if not any(parent.iterdir()):
                                parent.rmdir()
                                parent = parent.parent
                            else:
                                break
                        except OSError:
                            break
                            
                except OSError as e:
                    if not force:
                        raise RVSError(f"Cannot remove '{file_path}': {e}")
    
    def execute(self):
        """Legacy execute method."""
        print('Remove command executed')
