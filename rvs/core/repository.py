"""
Main repository implementation - improved version.
"""
import json
import hashlib
import zlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from ..exceptions import RepositoryError, ObjectError
from .hooks import Hook
from .index import Index

class RVS:
    """Main RVS repository class."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        rvs_path = self.repo_path / ".rvs"
        
        # Check if this is a worktree (where .rvs is a file, not a directory)
        if rvs_path.is_file():
            # This is a worktree - read the rvsdir path from the .rvs file
            with open(rvs_path, 'r') as f:
                content = f.read().strip()
                if content.startswith('rvsdir: '):
                    worktree_metadata_dir = Path(content[8:])  # Remove 'rvsdir: ' prefix
                else:
                    raise RepositoryError(f"Invalid .rvs file format: {content}")
            
            # The worktree metadata directory contains HEAD, index, etc.
            self.worktree_metadata_dir = worktree_metadata_dir
            
            # Read the main repository path from the gitdir file in worktree metadata
            gitdir_file = worktree_metadata_dir / "gitdir"
            if gitdir_file.exists():
                with open(gitdir_file, 'r') as f:
                    main_rvs_dir = Path(f.read().strip())
            else:
                raise RepositoryError("Worktree gitdir file not found")
            
            # Use main repository for objects, refs, etc.
            self.main_rvs_dir = main_rvs_dir
            self.rvs_dir = main_rvs_dir  # For compatibility
            self.objects_dir = main_rvs_dir / "objects"
            self.refs_dir = main_rvs_dir / "refs"
            self.heads_dir = self.refs_dir / "heads"
            self.index_file = worktree_metadata_dir / "index"  # Worktree has its own index
            self.head_file = worktree_metadata_dir / "HEAD"    # Worktree has its own HEAD
            self.config_file = main_rvs_dir / "config"
            self.is_worktree = True
        elif rvs_path.is_dir():
            # This is a main repository
            self.main_rvs_dir = rvs_path
            self.rvs_dir = rvs_path
            self.objects_dir = rvs_path / "objects"
            self.refs_dir = rvs_path / "refs"
            self.heads_dir = self.refs_dir / "heads"
            self.index_file = rvs_path / "index"
            self.head_file = rvs_path / "HEAD"
            self.config_file = rvs_path / "config"
            self.is_worktree = False
        else:
            # .rvs doesn't exist
            self.main_rvs_dir = rvs_path
            self.rvs_dir = rvs_path
            self.objects_dir = rvs_path / "objects"
            self.refs_dir = rvs_path / "refs"
            self.heads_dir = self.refs_dir / "heads"
            self.index_file = rvs_path / "index"
            self.head_file = rvs_path / "HEAD"
            self.config_file = rvs_path / "config"
            self.is_worktree = False
        
        self.hooks = Hook(self.repo_path)
    
    def _ensure_repo_exists(self):
        """Check if repository exists and raise error if not."""
        rvs_path = self.repo_path / ".rvs"
        if not rvs_path.exists():
            raise RepositoryError("Not a RVS repository. Run 'rvs init' first.")
        
        # For worktrees, also check that the main repository exists
        if self.is_worktree and not self.main_rvs_dir.exists():
            raise RepositoryError("Main repository not found. Worktree may be corrupted.")
    
    def _hash_content(self, content: bytes) -> str:
        """Generate SHA-1 hash for content."""
        return hashlib.sha1(content).hexdigest()
    
    def _write_object(self, content: bytes, obj_type: str = "blob") -> str:
        """Write object to objects directory with compression (Git-like format)."""
        header = f"{obj_type} {len(content)}\0".encode()
        full_content = header + content
        obj_hash = self._hash_content(full_content)
        
        obj_dir = self.objects_dir / obj_hash[:2]
        obj_dir.mkdir(parents=True, exist_ok=True)
        
        obj_file = obj_dir / obj_hash[2:]
        with open(obj_file, 'wb') as f:
            # Compress content with zlib
            compressed = zlib.compress(full_content)
            f.write(compressed)
        
        return obj_hash
    
    def _read_object(self, obj_hash: str) -> Tuple[str, bytes]:
        """Read compressed object from objects directory."""
        obj_file = self.objects_dir / obj_hash[:2] / obj_hash[2:]
        if not obj_file.exists():
            raise ObjectError(f"Object {obj_hash} not found")
        
        with open(obj_file, 'rb') as f:
            compressed = f.read()
        
        # Decompress content
        full_content = zlib.decompress(compressed)
        
        # Parse header
        null_pos = full_content.find(b'\0')
        header = full_content[:null_pos].decode()
        obj_type, size = header.split(' ')
        obj_content = full_content[null_pos + 1:]
        
        return obj_type, obj_content
    
    def _load_index(self) -> Dict[str, str]:
        """Load the staging area index using binary format."""
        if not self.index_file.exists():
            return {}
        
        # For worktrees, we need to load the index directly from the metadata directory
        if self.is_worktree:
            import json
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                # Convert to simple hash mapping for compatibility
                return {path: data['obj_hash'] for path, data in entries.items()}
            except (IOError, json.JSONDecodeError):
                return {}
        else:
            # For main repositories, use the Index class
            index = Index(self.repo_path)
            entries = index.load()
            # Convert to simple hash mapping for compatibility
            return {path: data['obj_hash'] for path, data in entries.items()}
    
    def _save_index(self, index: Dict[str, str]):
        """Save the staging area index using binary format."""
        # Convert to full entry format
        entries = {}
        for path, obj_hash in index.items():
            entries[path] = {'obj_hash': obj_hash}
        
        # For worktrees, save directly to the metadata directory
        if self.is_worktree:
            import json
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
        else:
            # For main repositories, use the Index class
            index_obj = Index(self.repo_path)
            index_obj.save(entries)
    
    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path like Git does."""
        # Convert to Path object and resolve relative components
        path = Path(file_path)
        
        # Get the absolute path and make it relative to repo root
        abs_path = (self.repo_path / path).resolve()
        try:
            rel_path = abs_path.relative_to(self.repo_path)
            # Convert back to string with forward slashes (Git style)
            normalized = str(rel_path).replace('\\', '/')
            return normalized
        except ValueError:
            # Path is outside repo, return as-is
            return file_path
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of a file's content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return self._write_object(content, "blob")
        except (IOError, OSError) as e:
            raise ObjectError(f"Failed to read file {file_path}: {e}")
    
    def init(self):
        """Initialize a new RVS repository."""
        if self.rvs_dir.exists():
            print(f"Reinitialized existing RVS repository in {self.rvs_dir}")
            return
        
        # Create directory structure (Git-like)
        self.rvs_dir.mkdir()
        self.objects_dir.mkdir()
        (self.objects_dir / "info").mkdir()
        (self.objects_dir / "pack").mkdir()
        self.refs_dir.mkdir()
        self.heads_dir.mkdir()
        (self.refs_dir / "tags").mkdir()
        (self.rvs_dir / "branches").mkdir()
        (self.rvs_dir / "info").mkdir()
        
        # Create initial HEAD pointing to main branch
        with open(self.head_file, 'w') as f:
            f.write("ref: refs/heads/main")
        
        # Create Git-style config file
        config_content = """[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        
        # Create description file
        description_file = self.rvs_dir / "description"
        with open(description_file, 'w') as f:
            f.write("Unnamed repository; edit this file 'description' to name the repository.\n")
        
        # Create empty index
        self._save_index({})
        
        # Install sample hooks (silently like Git)
        self.hooks.install_sample_hooks(show_message=False)
        
        print(f"Initialized empty RVS repository in {self.rvs_dir}")
    
    def add(self, file_paths: List[str]):
        """Add files to the staging area."""
        self._ensure_repo_exists()
        index = self._load_index()
        
        for file_path in file_paths:
            # Handle special case for current directory
            if file_path == ".":
                # Add all files in current directory recursively
                added_files = self._add_directory_recursive(self.repo_path, index)
                if not added_files:
                    print(f"warning: no files found in directory {file_path}")
                continue
            
            full_path = self.repo_path / file_path
            
            if not full_path.exists():
                print(f"fatal: pathspec '{file_path}' did not match any files")
                continue
            
            if full_path.is_file():
                # Normalize the path (remove ./ prefix, resolve relative paths)
                normalized_path = self._normalize_path(file_path)
                file_hash = self._get_file_hash(full_path)
                index[normalized_path] = file_hash
                # Git add is silent by default
            elif full_path.is_dir():
                # Recursively add all files in the directory
                added_files = self._add_directory_recursive(full_path, index)
                if not added_files:
                    print(f"warning: no files found in directory {file_path}")
            else:
                print(f"warning: {file_path} is not a file or directory, skipping")
        
        self._save_index(index)
    
    def _add_directory_recursive(self, dir_path: Path, index: Dict[str, str]) -> List[str]:
        """Recursively add all files in a directory to the index."""
        added_files = []
        
        # Get current commit files to check for deletions
        current_branch = self._get_current_branch()
        current_commit = self._get_branch_commit(current_branch)
        committed_files = {}
        if current_commit:
            try:
                commit_data = self._read_commit(current_commit)
                tree_hash = commit_data['tree']
                committed_files = self._read_tree(tree_hash)
            except Exception:
                pass  # No commits yet or error reading
        
        # Use rglob to recursively find all files
        working_files = set()
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                # Get relative path from repo root
                rel_path = file_path.relative_to(self.repo_path)
                rel_path_str = str(rel_path).replace('\\', '/')  # Normalize path separators
                
                # Skip .rvs file/directory and its contents
                if rel_path_str == '.rvs' or rel_path_str.startswith('.rvs/'):
                    continue
                
                working_files.add(rel_path_str)
                
                # Add to index
                file_hash = self._get_file_hash(file_path)
                index[rel_path_str] = file_hash
                added_files.append(rel_path_str)
        
        # Handle deletions: remove files from index that are tracked but missing from working directory
        # This only applies when adding the entire directory (like "git add .")
        if dir_path == self.repo_path:  # Only when adding from repo root
            files_to_remove = []
            for file_path in list(index.keys()):
                if file_path not in working_files and file_path in committed_files:
                    # File is in index and committed but not in working directory
                    # This means it was deleted from working directory and should be staged for deletion
                    files_to_remove.append(file_path)
            
            for file_path in files_to_remove:
                del index[file_path]
                added_files.append(f"deleted: {file_path}")
        
        return added_files
    
    def _group_files_by_directory(self, file_paths: List[str]) -> List[str]:
        """Group files by directory, showing directories instead of individual files when appropriate."""
        if not file_paths:
            return []
        
        # Separate files by their top-level directory
        directories = {}
        standalone_files = []
        
        for file_path in file_paths:
            parts = Path(file_path).parts
            if len(parts) > 1:
                # File is in a subdirectory
                top_dir = parts[0]
                if top_dir not in directories:
                    directories[top_dir] = []
                directories[top_dir].append(file_path)
            else:
                # File is in root directory
                standalone_files.append(file_path)
        
        result = []
        
        # Add standalone files
        result.extend(standalone_files)
        
        # For directories, show the directory name with trailing slash if it contains multiple files
        # or if all files in the directory are untracked
        for dir_name, files_in_dir in directories.items():
            # Check if this directory should be shown as a folder
            # We'll show it as a folder if it has multiple files or if it's a common directory
            if len(files_in_dir) >= 2 or dir_name in ['.git', '.rvs', 'examples', 'tests', 'src', 'docs']:
                result.append(f"{dir_name}/")
            else:
                # Single file in directory, show the full path
                result.extend(files_in_dir)
        
        return result
    
    def status(self):
        """Show repository status."""
        self._ensure_repo_exists()
        current_branch = self._get_current_branch()
        print(f"On branch {current_branch}")
        
        # Get current commit files
        current_commit = self._get_branch_commit(current_branch)
        committed_files = {}
        has_commits = False
        if current_commit:
            try:
                commit_data = self._read_commit(current_commit)
                tree_hash = commit_data['tree']
                committed_files = self._read_tree(tree_hash)
                has_commits = True
            except Exception:
                pass  # No commits yet or error reading
        
        # Show "No commits yet" if there are no commits
        if not has_commits:
            print("\nNo commits yet")
        
        # Get staged files
        index = self._load_index()
        
        # Get all files in working directory
        working_files = {}
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.repo_path)
                rel_path_str = str(rel_path).replace('\\', '/')  # Normalize path separators
                
                # Skip .rvs file/directory and its contents
                if rel_path_str == '.rvs' or rel_path_str.startswith('.rvs/'):
                    continue
                
                working_files[rel_path_str] = self._get_file_hash(file_path)
        
        # Categorize files
        staged_files = set(index.keys())
        committed_file_names = set(committed_files.keys())
        working_file_names = set(working_files.keys())
        
        # Files staged for commit
        changes_to_commit = []
        for file_path in staged_files:
            if file_path not in committed_files:
                changes_to_commit.append(("new file", file_path))
            elif index[file_path] != committed_files[file_path]:
                changes_to_commit.append(("modified", file_path))
        
        # Modified files (files that differ between working directory and what's staged/committed)
        modified_files = []
        for file_path in working_file_names:
            if file_path in index:
                # File is staged - check if working version differs from staged version
                if working_files[file_path] != index[file_path]:
                    modified_files.append(file_path)
            elif file_path in committed_files:
                # File not staged but exists in commit - check if working version differs from committed
                if working_files[file_path] != committed_files[file_path]:
                    modified_files.append(file_path)
        
        # Files staged for deletion (in commit but not in index)
        for file_path in committed_file_names:
            if file_path not in staged_files:
                # File exists in commit but not in index - this means it was explicitly staged for deletion
                changes_to_commit.append(("deleted", file_path))
        
        # Deleted files (in commit and index but not in working directory)
        deleted_files = []
        for file_path in committed_file_names:
            if file_path in index and file_path not in working_file_names:
                # File exists in commit and index but not in working directory
                # This is a deletion that's not staged (like Git behavior)
                deleted_files.append(file_path)
        
        # Untracked files (in working dir but not committed and not staged)
        untracked_files = []
        for file_path in working_file_names:
            if file_path not in committed_files and file_path not in index:
                untracked_files.append(file_path)
        
        # Group untracked files by directory for cleaner display
        untracked_display = self._group_files_by_directory(untracked_files)
        
        # Display results
        if changes_to_commit:
            print("\nChanges to be committed:")
            if has_commits:
                print('  (use "rvs restore --staged <file>..." to unstage)')
            else:
                print('  (use "rvs rm --cached <file>..." to unstage)')
            for status_type, file_path in changes_to_commit:
                print(f"\t{status_type}:   {file_path}")
        
        if modified_files or deleted_files:
            print("\nChanges not staged for commit:")
            print("  (use 'rvs add <file>...' to update what will be committed)")
            print("  (use 'rvs restore <file>...' to discard changes in working directory)")
            for file_path in modified_files:
                print(f"\tmodified:   {file_path}")
            for file_path in deleted_files:
                print(f"\tdeleted:    {file_path}")
        
        if untracked_display:
            print("\nUntracked files:")
            print("  (use 'rvs add <file>...' to include in what will be committed)")
            for item in sorted(untracked_display):
                print(f"\t{item}")
        
        # Final status summary
        if not changes_to_commit and not modified_files and not deleted_files:
            if untracked_display:
                print("\nnothing added to commit but untracked files present (use \"rvs add\" to track)")
            elif has_commits:
                print("\nnothing to commit, working tree clean")
            elif not has_commits and not untracked_display:
                print("\nnothing to commit (create/copy files and use \"rvs add\" to track)")
    
    def log(self, max_count: int = 10, oneline: bool = False, graph: bool = False):
        """Show commit history with optional graph."""
        self._ensure_repo_exists()
        current_branch = self._get_current_branch()
        commit_hash = self._get_branch_commit(current_branch)
        
        if not commit_hash:
            print("No commits found")
            return
        
        # Collect commits
        commits = []
        visited = set()
        
        while commit_hash and commit_hash not in visited and len(commits) < max_count:
            visited.add(commit_hash)
            commit_data = self._read_commit(commit_hash)
            commits.append({
                'hash': commit_hash,
                'message': commit_data['message'],
                'date': commit_data['date'],
                'parents': [commit_data['parent']] if commit_data.get('parent') else []
            })
            commit_hash = commit_data.get('parent')
        
        if graph:
            # Print with graph
            from ..commands.log import LogCommand
            log_cmd = LogCommand(self)
            log_cmd._print_commit_graph(commits, current_branch)
        else:
            # Print without graph
            for i, commit in enumerate(commits):
                commit_hash = commit['hash']
                is_head = i == 0
                
                if oneline:
                    short_hash = commit_hash[:7]
                    message = commit['message'].split('\n')[0]
                    branch_info = f" (HEAD -> {current_branch})" if is_head else ""
                    print(f"{short_hash}{branch_info} {message}")
                else:
                    branch_info = f" (HEAD -> {current_branch})" if is_head else ""
                    print(f"commit {commit_hash}{branch_info}")
                    print(f"Author: {commit.get('author', 'RVS User')} <rvs@example.com>")
                    
                    # Format date like Git: "Sat Aug 16 13:43:18 2025 -0500"
                    import datetime
                    import time
                    timestamp = commit.get('timestamp', 0)
                    if timestamp == 0:
                        # Fallback to current time if timestamp is missing
                        timestamp = int(time.time())
                    
                    dt = datetime.datetime.fromtimestamp(timestamp)
                    # Get timezone offset
                    tz_offset = time.strftime("%z")
                    if not tz_offset:
                        tz_offset = "+0000"
                    
                    formatted_date = dt.strftime("%a %b %d %H:%M:%S %Y ") + tz_offset
                    
                    print(f"Date:   {formatted_date}")
                    print()
                    for line in commit['message'].split('\n'):
                        print(f"    {line}")
                    print()
    
    def _read_commit(self, commit_hash: str) -> Dict[str, Any]:
        """Read a commit object."""
        obj_type, content = self._read_object(commit_hash)
        if obj_type != "commit":
            raise ObjectError(f"Expected commit object, got {obj_type}")
        
        return json.loads(content.decode())
    
    def _get_current_branch(self) -> str:
        """Get current branch name."""
        if not self.head_file.exists():
            return "main"
        
        with open(self.head_file, 'r') as f:
            head_content = f.read().strip()
        
        if head_content.startswith("ref: refs/heads/"):
            return head_content[16:]  # Remove "ref: refs/heads/"
        
        # For worktrees, if HEAD contains a commit hash, we're in detached HEAD state
        if self.is_worktree and len(head_content) == 40:  # SHA-1 hash length
            return "HEAD"  # Detached HEAD
        
        return "main"
    
    def _get_branch_commit(self, branch: str) -> Optional[str]:
        """Get the latest commit hash for a branch."""
        # Special case for detached HEAD in worktrees
        if self.is_worktree and branch == "HEAD":
            if self.head_file.exists():
                with open(self.head_file, 'r') as f:
                    head_content = f.read().strip()
                    # If it's a commit hash (not a ref), return it
                    if not head_content.startswith("ref: ") and len(head_content) == 40:
                        return head_content
        
        branch_file = self.heads_dir / branch
        if not branch_file.exists():
            return None
        
        with open(branch_file, 'r') as f:
            return f.read().strip()
    
    def commit(self, message: str):
        """Create a new commit with staged changes."""
        self._ensure_repo_exists()
        
        # Check if there are any changes to commit (like Git does)
        current_branch = self._get_current_branch()
        parent_commit = self._get_branch_commit(current_branch)
        index = self._load_index()
        
        # Get parent commit files
        parent_files = {}
        if parent_commit:
            try:
                parent_data = self._read_commit(parent_commit)
                parent_tree_hash = parent_data['tree']
                parent_files = self._read_tree(parent_tree_hash)
            except Exception:
                pass  # No parent or error reading parent
        
        # Check if there are any actual changes to commit
        has_changes = False
        
        # Check for new files or modified files in index
        for file_path, file_hash in index.items():
            if file_path not in parent_files or parent_files[file_path] != file_hash:
                has_changes = True
                break
        
        # Check for deleted files (files in parent but not in index)
        if not has_changes:
            for file_path in parent_files.keys():
                if file_path not in index:
                    # This would be a deletion, but we need to check if the file still exists in working directory
                    # If it exists in working dir but not in index, it's not staged for deletion
                    file_full_path = self.repo_path / file_path
                    if not file_full_path.exists():
                        has_changes = True
                        break
        
        # If no changes, show status-like output and return
        if not has_changes:
            # Show current status like Git does
            print(f"On branch {current_branch}")
            
            # Get all files in working directory
            working_files = {}
            for file_path in self.repo_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.repo_path)
                    rel_path_str = str(rel_path).replace('\\', '/')  # Normalize path separators
                    
                    # Skip .rvs file/directory and its contents
                    if rel_path_str == '.rvs' or rel_path_str.startswith('.rvs/'):
                        continue
                    
                    working_files[rel_path_str] = self._get_file_hash(file_path)
            
            # Find untracked files
            untracked_files = []
            for file_path in working_files.keys():
                if file_path not in parent_files and file_path not in index:
                    untracked_files.append(file_path)
            
            # Group untracked files by directory for cleaner display
            untracked_display = self._group_files_by_directory(untracked_files)
            
            if untracked_display:
                print("Untracked files:")
                print('  (use "rvs add <file>..." to include in what will be committed)')
                for item in sorted(untracked_display):
                    print(f"\t{item}")
                print("\nnothing added to commit but untracked files present (use \"rvs add\" to track)")
            else:
                print("\nnothing to commit, working tree clean")
            return
        
        # Run pre-commit hook
        if not self.hooks.run_hook("pre-commit"):
            print("Commit aborted by pre-commit hook")
            return
        
        # Start with files from parent commit (if any)
        commit_files = parent_files.copy()
        
        # Update with staged files (this creates a cumulative snapshot)
        commit_files.update(index)
        
        # Calculate file statistics
        files_changed = 0
        insertions = 0
        deletions = 0
        new_files = []
        modified_files = []
        deleted_files = []
        
        # Check files in index (new or modified)
        for file_path in index.keys():
            if file_path not in parent_files:
                # New file
                new_files.append(file_path)
                files_changed += 1
                # For new files, count lines as insertions
                try:
                    file_full_path = self.repo_path / file_path
                    if file_full_path.exists():
                        with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            insertions += lines
                except:
                    pass  # If we can't read the file, just skip line counting
            elif index[file_path] != parent_files[file_path]:
                # Modified file
                modified_files.append(file_path)
                files_changed += 1
                # For simplicity, we'll just count it as 0 insertions/deletions
                # A full implementation would need to diff the files
        
        # Check for deleted files (files in parent but not in index)
        for file_path in parent_files.keys():
            if file_path not in index:
                # Deleted file
                deleted_files.append(file_path)
                files_changed += 1
                # For deleted files, count lines as deletions
                try:
                    # We can't read the deleted file from working directory,
                    # but we can read it from the parent commit
                    obj_type, content = self._read_object(parent_files[file_path])
                    if obj_type == "blob":
                        lines = len(content.decode('utf-8', errors='ignore').splitlines())
                        deletions += lines
                except:
                    pass  # If we can't read the file, just skip line counting
        
        # Create tree from all files (parent + staged)
        tree_hash = self._create_tree(commit_files)
        
        # Create commit
        commit_hash = self._create_commit(tree_hash, message, parent_commit)
        
        # Update branch reference
        self._set_branch_commit(current_branch, commit_hash)
        
        # Update index to match the new commit state (like Git does)
        # Instead of clearing the index, set it to match the committed files
        self._save_index(commit_files)
        
        # Run post-commit hook
        self.hooks.run_hook("post-commit")
        
        # Format output like Git
        is_root_commit = parent_commit is None
        root_commit_text = " (root-commit)" if is_root_commit else ""
        short_hash = commit_hash[:7]
        
        print(f"[{current_branch}{root_commit_text} {short_hash}] {message}")
        
        # File statistics
        if files_changed > 0:
            stats_parts = []
            if files_changed == 1:
                stats_parts.append("1 file changed")
            else:
                stats_parts.append(f"{files_changed} files changed")
            
            if insertions > 0:
                stats_parts.append(f"{insertions} insertions(+)")
            if deletions > 0:
                stats_parts.append(f"{deletions} deletions(-)")
            
            print(f" {', '.join(stats_parts)}")
        
        # Show file changes
        for file_path in new_files:
            print(f" create mode 100644 {file_path}")
        for file_path in deleted_files:
            print(f" delete mode 100644 {file_path}")
    
    def _create_tree(self, file_dict: Dict[str, str]) -> str:
        """Create a tree object from a dictionary of files."""
        tree_entries = []
        
        for file_path, file_hash in sorted(file_dict.items()):
            # Simple tree format: "blob <hash> <filename>"
            tree_entries.append(f"blob {file_hash} {file_path}")
        
        tree_content = "\n".join(tree_entries).encode()
        return self._write_object(tree_content, "tree")
    
    def _read_tree(self, tree_hash: str) -> Dict[str, str]:
        """Read a tree object and return file dictionary."""
        obj_type, content = self._read_object(tree_hash)
        if obj_type != "tree":
            raise ObjectError(f"Expected tree object, got {obj_type}")
        
        file_dict = {}
        if content:
            for line in content.decode().split('\n'):
                if line.strip():
                    parts = line.split(' ', 2)
                    if len(parts) == 3:
                        obj_type, obj_hash, filename = parts
                        file_dict[filename] = obj_hash
        
        return file_dict
    
    def _create_commit(self, tree_hash: str, message: str, parent: Optional[str] = None) -> str:
        """Create a commit object."""
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
        return self._write_object(commit_content, "commit")
    
    def _set_branch_commit(self, branch: str, commit_hash: str):
        """Set the commit hash for a branch."""
        self.heads_dir.mkdir(parents=True, exist_ok=True)
        branch_file = self.heads_dir / branch
        with open(branch_file, 'w') as f:
            f.write(commit_hash)
    
    def branch(self, branch_name: str = None, list_branches: bool = False):
        """Create or list branches."""
        self._ensure_repo_exists()
        
        if list_branches or branch_name is None:
            current_branch = self._get_current_branch()
            
            if self.heads_dir.exists():
                for branch_file in self.heads_dir.iterdir():
                    prefix = "* " if branch_file.name == current_branch else "  "
                    print(f"{prefix}{branch_file.name}")
            else:
                print(f"* {current_branch}")
        
        elif branch_name:
            # Create new branch
            current_commit = self._get_branch_commit(self._get_current_branch())
            if current_commit:
                self._set_branch_commit(branch_name, current_commit)
                # Git is silent when creating branches
            else:
                print("fatal: Not a valid object name: 'HEAD'.")
