"""Ls-files command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List, Set
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class LsFilesCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('ls-files', help='Show information about files in the index and working tree')
        parser.add_argument('pathspec', nargs='*', help='Limit to specific paths')
        parser.add_argument('-c', '--cached', action='store_true',
                          help='Show cached files in the output (default)')
        parser.add_argument('-d', '--deleted', action='store_true',
                          help='Show deleted files in the output')
        parser.add_argument('-m', '--modified', action='store_true',
                          help='Show modified files in the output')
        parser.add_argument('-o', '--others', action='store_true',
                          help='Show other (untracked) files in the output')
        parser.add_argument('-i', '--ignored', action='store_true',
                          help='Show only ignored files in the output')
        parser.add_argument('-s', '--stage', action='store_true',
                          help='Show staged contents\' mode bits, object name and stage number')
        parser.add_argument('-u', '--unmerged', action='store_true',
                          help='Show unmerged files in the output')
        parser.add_argument('-k', '--killed', action='store_true',
                          help='Show files on the filesystem that need to be removed')
        parser.add_argument('-z', '--null', action='store_true',
                          help='\\0 line termination on output')
        parser.add_argument('--exclude-standard', action='store_true',
                          help='Add the standard git exclusions')
        parser.add_argument('-x', '--exclude', action='append',
                          help='Skip untracked files matching pattern')
        parser.add_argument('-X', '--exclude-from', 
                          help='Read exclude patterns from file')
        return parser
    
    def execute_from_args(self, args: Any):
        self.ls_files(
            pathspec=args.pathspec,
            cached=args.cached,
            deleted=args.deleted,
            modified=args.modified,
            others=args.others,
            ignored=args.ignored,
            stage=args.stage,
            unmerged=args.unmerged,
            killed=args.killed,
            null_terminate=args.null,
            exclude_standard=args.exclude_standard,
            exclude_patterns=args.exclude or [],
            exclude_from=args.exclude_from
        )
    
    def ls_files(self, pathspec: List[str] = None, cached: bool = False,
                 deleted: bool = False, modified: bool = False, others: bool = False,
                 ignored: bool = False, stage: bool = False, unmerged: bool = False,
                 killed: bool = False, null_terminate: bool = False,
                 exclude_standard: bool = False, exclude_patterns: List[str] = None,
                 exclude_from: str = None):
        """List files in the index and working tree."""
        self.repo._ensure_repo_exists()
        
        # Default to cached if no specific option is given
        if not any([cached, deleted, modified, others, ignored, stage, unmerged, killed]):
            cached = True
        
        # Load index
        index = self.repo._load_index()
        
        # Get committed files for comparison
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
        
        # Get working tree files
        working_files = self._get_working_files()
        
        # Prepare exclude patterns
        exclude_patterns = exclude_patterns or []
        if exclude_from:
            try:
                with open(exclude_from, 'r') as f:
                    exclude_patterns.extend(line.strip() for line in f if line.strip())
            except IOError:
                pass
        
        if exclude_standard:
            exclude_patterns.extend(['.rvs', '*.pyc', '__pycache__', '.DS_Store'])
        
        # Collect files to show
        files_to_show = []
        
        if cached or stage:
            files_to_show.extend(self._get_cached_files(index, stage, pathspec))
        
        if deleted:
            files_to_show.extend(self._get_deleted_files(index, working_files, pathspec))
        
        if modified:
            files_to_show.extend(self._get_modified_files(index, working_files, pathspec))
        
        if others:
            files_to_show.extend(self._get_untracked_files(
                index, working_files, exclude_patterns, pathspec))
        
        if ignored:
            files_to_show.extend(self._get_ignored_files(
                index, working_files, exclude_patterns, pathspec))
        
        # Remove duplicates and sort
        files_to_show = sorted(set(files_to_show))
        
        # Output
        separator = '\0' if null_terminate else '\n'
        for file_info in files_to_show:
            print(file_info, end=separator)
    
    def _get_working_files(self) -> Set[str]:
        """Get all files in working tree."""
        working_files = set()
        for file_path in self.repo.repo_path.rglob('*'):
            if file_path.is_file() and not str(file_path).startswith(str(self.repo.rvs_dir)):
                rel_path = file_path.relative_to(self.repo.repo_path)
                working_files.add(str(rel_path))
        return working_files
    
    def _get_cached_files(self, index: dict, stage: bool, pathspec: List[str]) -> List[str]:
        """Get cached (staged) files."""
        files = []
        
        # If index is empty, show files from the current commit
        if not index:
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
            
            for file_path, file_hash in committed_files.items():
                if self._matches_pathspec(file_path, pathspec):
                    if stage:
                        # Show stage information
                        files.append(f"100644 {file_hash} 0\t{file_path}")
                    else:
                        files.append(file_path)
        else:
            # Show files from index
            for file_path, file_hash in index.items():
                if self._matches_pathspec(file_path, pathspec):
                    if stage:
                        # Show stage information
                        files.append(f"100644 {file_hash} 0\t{file_path}")
                    else:
                        files.append(file_path)
        return files
    
    def _get_deleted_files(self, index: dict, working_files: Set[str], pathspec: List[str]) -> List[str]:
        """Get deleted files (in index but not in working tree)."""
        files = []
        for file_path in index.keys():
            if file_path not in working_files and self._matches_pathspec(file_path, pathspec):
                files.append(file_path)
        return files
    
    def _get_modified_files(self, index: dict, working_files: Set[str], pathspec: List[str]) -> List[str]:
        """Get modified files (different between index and working tree)."""
        files = []
        for file_path in index.keys():
            if file_path in working_files and self._matches_pathspec(file_path, pathspec):
                # Check if file is modified
                full_path = self.repo.repo_path / file_path
                try:
                    current_hash = self.repo._get_file_hash(full_path)
                    if current_hash != index[file_path]:
                        files.append(file_path)
                except Exception:
                    pass
        return files
    
    def _get_untracked_files(self, index: dict, working_files: Set[str], 
                           exclude_patterns: List[str], pathspec: List[str]) -> List[str]:
        """Get untracked files (in working tree but not in index)."""
        files = []
        for file_path in working_files:
            if (file_path not in index and 
                self._matches_pathspec(file_path, pathspec) and
                not self._is_excluded(file_path, exclude_patterns)):
                files.append(file_path)
        return files
    
    def _get_ignored_files(self, index: dict, working_files: Set[str],
                          exclude_patterns: List[str], pathspec: List[str]) -> List[str]:
        """Get ignored files."""
        files = []
        for file_path in working_files:
            if (file_path not in index and 
                self._matches_pathspec(file_path, pathspec) and
                self._is_excluded(file_path, exclude_patterns)):
                files.append(file_path)
        return files
    
    def _matches_pathspec(self, file_path: str, pathspec: List[str]) -> bool:
        """Check if file matches pathspec."""
        if not pathspec:
            return True
        
        for pattern in pathspec:
            if file_path.startswith(pattern):
                return True
            if pattern == '.' or pattern == file_path:
                return True
        return False
    
    def _is_excluded(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """Check if file matches exclude patterns."""
        import fnmatch
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
            if fnmatch.fnmatch(Path(file_path).name, pattern):
                return True
        return False
    
    def execute(self):
        """Legacy execute method."""
        print('Ls-files command executed')
