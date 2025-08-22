"""
Git object implementations (blob, tree, commit).
"""
import json
import hashlib
import zlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from ..exceptions import ObjectError

class GitObject:
    """Base class for all Git objects."""
    
    def __init__(self, content: bytes, obj_type: str):
        self.content = content
        self.obj_type = obj_type
        self._hash = None
    
    @property
    def hash(self) -> str:
        """Get the SHA-1 hash of this object."""
        if self._hash is None:
            header = f"{self.obj_type} {len(self.content)}\0".encode()
            full_content = header + self.content
            self._hash = hashlib.sha1(full_content).hexdigest()
        return self._hash
    
    def serialize(self) -> bytes:
        """Serialize object for storage."""
        header = f"{self.obj_type} {len(self.content)}\0".encode()
        return header + self.content
    
    @classmethod
    def deserialize(cls, data: bytes) -> Tuple[str, bytes]:
        """Deserialize object from storage."""
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ObjectError("Invalid object format: no null separator found")
        
        header = data[:null_pos].decode()
        try:
            obj_type, size = header.split(' ')
        except ValueError:
            raise ObjectError(f"Invalid object header: {header}")
        
        content = data[null_pos + 1:]
        expected_size = int(size)
        
        if len(content) != expected_size:
            raise ObjectError(f"Object size mismatch: expected {expected_size}, got {len(content)}")
        
        return obj_type, content

class Blob(GitObject):
    """Represents a file blob object."""
    
    def __init__(self, content: bytes):
        super().__init__(content, "blob")
    
    @classmethod
    def from_file(cls, file_path: Path) -> 'Blob':
        """Create a blob from a file."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return cls(content)
        except (IOError, OSError) as e:
            raise ObjectError(f"Failed to read file {file_path}: {e}")

class Tree(GitObject):
    """Represents a tree object."""
    
    def __init__(self, entries: Dict[str, str]):
        self.entries = entries
        content = self._serialize_entries()
        super().__init__(content, "tree")
    
    def _serialize_entries(self) -> bytes:
        """Serialize tree entries."""
        tree_entries = []
        for file_path, file_hash in sorted(self.entries.items()):
            tree_entries.append(f"blob {file_hash} {file_path}")
        return "\n".join(tree_entries).encode()
    
    @classmethod
    def from_content(cls, content: bytes) -> 'Tree':
        """Create a tree from serialized content."""
        entries = {}
        if content:
            for line in content.decode().split('\n'):
                if line.strip():
                    parts = line.split(' ', 2)
                    if len(parts) == 3:
                        obj_type, obj_hash, filename = parts
                        entries[filename] = obj_hash
        
        tree = cls.__new__(cls)
        tree.entries = entries
        tree.content = content
        tree.obj_type = "tree"
        tree._hash = None
        return tree

class Commit(GitObject):
    """Represents a commit object."""
    
    def __init__(self, tree_hash: str, message: str, parent: Optional[str] = None, 
                 author: str = "RVS User", merge_parent: Optional[str] = None):
        self.tree_hash = tree_hash
        self.message = message
        self.parent = parent
        self.merge_parent = merge_parent
        self.author = author
        self.timestamp = int(time.time())
        self.date = datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        content = self._serialize_commit()
        super().__init__(content, "commit")
    
    def _serialize_commit(self) -> bytes:
        """Serialize commit data."""
        commit_data = {
            "tree": self.tree_hash,
            "parent": self.parent,
            "message": self.message,
            "timestamp": self.timestamp,
            "date": self.date,
            "author": self.author
        }
        
        if self.merge_parent:
            commit_data["merge_parent"] = self.merge_parent
        
        return json.dumps(commit_data, indent=2).encode()
    
    @classmethod
    def from_content(cls, content: bytes) -> 'Commit':
        """Create a commit from serialized content."""
        try:
            commit_data = json.loads(content.decode())
        except json.JSONDecodeError as e:
            raise ObjectError(f"Invalid commit format: {e}")
        
        commit = cls.__new__(cls)
        commit.tree_hash = commit_data.get("tree")
        commit.message = commit_data.get("message", "")
        commit.parent = commit_data.get("parent")
        commit.merge_parent = commit_data.get("merge_parent")
        commit.author = commit_data.get("author", "RVS User")
        commit.timestamp = commit_data.get("timestamp", int(time.time()))
        commit.date = commit_data.get("date", "")
        commit.content = content
        commit.obj_type = "commit"
        commit._hash = None
        return commit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert commit to dictionary."""
        return {
            "tree": self.tree_hash,
            "parent": self.parent,
            "merge_parent": self.merge_parent,
            "message": self.message,
            "timestamp": self.timestamp,
            "date": self.date,
            "author": self.author
        }
