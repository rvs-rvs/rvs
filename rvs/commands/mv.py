"""Move/rename command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class MvCommand(BaseCommand):
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('mv', help='Move or rename a file, a directory, or a symlink')
        parser.add_argument('source', help='Source file or directory')
        parser.add_argument('destination', help='Destination file or directory')
        parser.add_argument('-f', '--force', action='store_true', help='Force move/rename')
        parser.add_argument('-k', action='store_true', help='Skip move/rename errors')
        parser.add_argument('-n', '--dry-run', action='store_true', help='Show what would be moved')
        parser.add_argument('-v', '--verbose', action='store_true', help='Be verbose')
        return parser
    
    def execute_from_args(self, args: Any):
        self.move_file(
            source=args.source,
            destination=args.destination,
            force=args.force,
            skip_errors=args.k,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
    
    def move_file(self, source: str, destination: str, force: bool = False, 
                  skip_errors: bool = False, dry_run: bool = False, verbose: bool = False):
        """Move or rename a file/directory."""
        self.repo._ensure_repo_exists()
        
        source_path = Path(source)
        dest_path = Path(destination)
        
        # Convert to absolute paths relative to repo
        source_full = (self.repo.repo_path / source_path).resolve()
        dest_full = (self.repo.repo_path / dest_path).resolve()
        
        # Validate source exists
        if not source_full.exists():
            if skip_errors:
                if verbose:
                    print(f"Skipping {source}: does not exist")
                return
            raise RVSError(f"fatal: not under version control, source={source}")
        
        # Check if source is under version control
        if not self._is_tracked(source):
            if skip_errors:
                if verbose:
                    print(f"Skipping {source}: not under version control")
                return
            raise RVSError(f"fatal: not under version control, source={source}")
        
        # Check if destination already exists
        if dest_full.exists() and not force:
            if skip_errors:
                if verbose:
                    print(f"Skipping {source} -> {destination}: destination exists")
                return
            raise RVSError(f"fatal: destination exists, source={source}, destination={destination}")
        
        # Normalize paths for index
        source_norm = self.repo._normalize_path(source)
        dest_norm = self.repo._normalize_path(str(dest_path))
        
        if dry_run:
            print(f"Renaming {source} to {destination}")
            return
        
        # Perform the move
        try:
            # Create destination directory if needed
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            source_full.rename(dest_full)
            
            # Update the index
            self._update_index_for_move(source_norm, dest_norm)
            
            if verbose:
                print(f"Renaming {source} to {destination}")
            
        except OSError as e:
            if skip_errors:
                if verbose:
                    print(f"Skipping {source}: {e}")
                return
            raise RVSError(f"fatal: renaming '{source}' failed: {e}")
    
    def _is_tracked(self, file_path: str) -> bool:
        """Check if file is tracked in the index."""
        try:
            index = self.repo._load_index()
            normalized_path = self.repo._normalize_path(file_path)
            return normalized_path in index
        except Exception:
            return False
    
    def _update_index_for_move(self, source_path: str, dest_path: str):
        """Update index to reflect the move."""
        try:
            index = self.repo._load_index()
            
            if source_path in index:
                # Move the entry in the index
                file_hash = index[source_path]
                del index[source_path]
                index[dest_path] = file_hash
                
                # Save updated index
                self.repo._save_index(index)
            
        except Exception as e:
            raise RVSError(f"Failed to update index: {e}")
    
    def execute(self):
        """Legacy execute method."""
        print('Move command executed')