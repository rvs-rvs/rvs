"""
Index (staging area) management with simplified format.
"""
import json
from pathlib import Path
from typing import Dict
from ..exceptions import IndexError

class Index:
    """Manages the staging area with JSON format for simplicity and reliability."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.index_file = repo_path / ".rvs" / "index"
        self.entries = {}
    
    def load(self) -> Dict[str, Dict]:
        """Load index from JSON file."""
        if not self.index_file.exists():
            return {}
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.entries = data
                return data
        except (IOError, json.JSONDecodeError):
            # If we can't read the index file, return empty index
            return {}
    
    def save(self, entries: Dict[str, Dict]):
        """Save index to JSON file."""
        self.entries = entries
        
        # Create a temporary file first, then rename to avoid corruption
        temp_file = self.index_file.with_suffix('.tmp')
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
            
            # Atomically replace the index file
            if self.index_file.exists():
                self.index_file.unlink()
            temp_file.rename(self.index_file)
            
        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_file.exists():
                temp_file.unlink()
            raise IndexError(f"Failed to save index: {e}")