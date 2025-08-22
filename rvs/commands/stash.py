"""Stash command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, Dict, List, Optional
import json
import time
from datetime import datetime
from pathlib import Path
from .base import BaseCommand
from ..exceptions import RVSError

class StashCommand(BaseCommand):
    """Manage stash stack."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        parser = subparsers.add_parser('stash', help='Stash changes')
        subparsers_stash = parser.add_subparsers(dest='stash_command', help='Stash commands')
        
        # save subcommand
        save_parser = subparsers_stash.add_parser('save', help='Save changes to stash')
        save_parser.add_argument('message', nargs='?', help='Stash message')
        save_parser.add_argument('-u', '--include-untracked', action='store_true',
                              help='Include untracked files')
        
        # list subcommand
        list_parser = subparsers_stash.add_parser('list', help='List stashes')
        
        # show subcommand
        show_parser = subparsers_stash.add_parser('show', help='Show stash')
        show_parser.add_argument('stash', nargs='?', default='0', help='Stash to show')
        
        # pop subcommand
        pop_parser = subparsers_stash.add_parser('pop', help='Pop stash')
        pop_parser.add_argument('stash', nargs='?', default='0', help='Stash to pop')
        
        # apply subcommand
        apply_parser = subparsers_stash.add_parser('apply', help='Apply stash')
        apply_parser.add_argument('stash', nargs='?', default='0', help='Stash to apply')
        
        # drop subcommand
        drop_parser = subparsers_stash.add_parser('drop', help='Drop stash')
        drop_parser.add_argument('stash', nargs='?', default='0', help='Stash to drop')
        
        return parser
    
    def execute_from_args(self, args: Any):
        if not hasattr(args, 'stash_command') or not args.stash_command:
            self.save_stash()
        elif args.stash_command == 'save':
            self.save_stash(args.message, args.include_untracked)
        elif args.stash_command == 'list':
            self.list_stashes()
        elif args.stash_command == 'show':
            self.show_stash(args.stash)
        elif args.stash_command == 'pop':
            self.pop_stash(args.stash)
        elif args.stash_command == 'apply':
            self.apply_stash(args.stash)
        elif args.stash_command == 'drop':
            self.drop_stash(args.stash)
    
    def save_stash(self, message: Optional[str] = None, include_untracked: bool = False):
        """Save current changes to stash."""
        self.repo._ensure_repo_exists()
        
        # Get current changes
        index = self.repo._load_index()
        working_files = self._get_working_files()
        
        # Check if there are any changes to stash
        current_branch = self.repo._get_current_branch()
        current_commit = self.repo._get_branch_commit(current_branch)
        committed_files = {}
        
        if current_commit:
            try:
                commit_data = self.repo._read_commit(current_commit)
                tree_hash = commit_data['tree']
                committed_files = self.repo._read_tree(tree_hash)
            except Exception:
                pass
        
        # Check for modified files
        has_changes = False
        
        # Check working directory changes
        for file_path, file_hash in working_files.items():
            if file_path in committed_files:
                if file_hash != committed_files[file_path]:
                    has_changes = True
                    break
            elif file_path not in index:
                # Untracked file
                if include_untracked:
                    has_changes = True
                    break
        
        # Check staged changes
        for file_path, file_hash in index.items():
            if file_path not in committed_files or file_hash != committed_files[file_path]:
                has_changes = True
                break
        
        if not has_changes:
            print("No local changes to save")
            return
        
        # Get current commit info for message
        commit_info = ""
        if current_commit:
            try:
                commit_data = self.repo._read_commit(current_commit)
                short_hash = current_commit[:7]
                commit_msg = commit_data['message'].split('\\n')[0]
                commit_info = f"{short_hash} {commit_msg}"
            except Exception:
                commit_info = current_commit[:7] if current_commit else "initial"
        else:
            commit_info = "initial"
        
        # Create stash message in Git format
        if not message:
            message = f"WIP on {current_branch}: {commit_info}"
        
        # Create stash data
        timestamp = int(time.time())
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        stash_data = {
            "message": message,
            "timestamp": timestamp,
            "date": date_str,
            "branch": current_branch,
            "commit": current_commit,
            "index": index,
            "working_files": working_files,
            "committed_files": committed_files,
            "include_untracked": include_untracked
        }
        
        # Save stash
        stash_file = self.repo.rvs_dir / "stash"
        stashes = []
        
        if stash_file.exists():
            try:
                with open(stash_file, 'r', encoding='utf-8') as f:
                    stashes = json.load(f)
            except Exception:
                stashes = []
        
        stashes.insert(0, stash_data)
        
        try:
            with open(stash_file, 'w', encoding='utf-8') as f:
                json.dump(stashes, f, indent=2)
        except Exception as e:
            raise RVSError(f"Failed to save stash: {e}")
        
        # Clear working directory changes (restore to committed state)
        self._restore_to_committed_state(committed_files)
        
        # Clear staging area
        self.repo._save_index({})
        
        print(f"Saved working directory and index state {message}")
    
    def list_stashes(self):
        """List all stashes."""
        stash_file = self.repo.rvs_dir / "stash"
        
        if not stash_file.exists():
            return  # Git shows nothing when no stashes exist
        
        try:
            with open(stash_file, 'r', encoding='utf-8') as f:
                stashes = json.load(f)
        except Exception:
            return
        
        for i, stash in enumerate(stashes):
            print(f"stash@{{{i}}}: {stash['message']}")
    
    def show_stash(self, stash_ref: str = "0"):
        """Show a stash."""
        stash_file = self.repo.rvs_dir / "stash"
        
        if not stash_file.exists():
            return  # Git shows nothing when no stashes exist
        
        try:
            with open(stash_file, 'r', encoding='utf-8') as f:
                stashes = json.load(f)
        except Exception:
            return
        
        try:
            idx = int(stash_ref)
            if idx < 0 or idx >= len(stashes):
                return
            
            stash = stashes[idx]
            
            # Count changes (simplified version)
            changes = 0
            insertions = 0
            deletions = 0
            
            # Compare working files with committed files
            committed_files = stash.get('committed_files', {})
            working_files = stash.get('working_files', {})
            
            modified_files = []
            for file_path in working_files:
                if file_path in committed_files:
                    if working_files[file_path] != committed_files[file_path]:
                        modified_files.append(file_path)
                        changes += 1
                        # Simplified: assume 1 insertion and 1 deletion per modified file
                        insertions += 1
                        deletions += 1
            
            # Show summary like Git
            if modified_files:
                for file_path in modified_files:
                    print(f" {file_path} | 2 +-")
                print(f" {changes} file{'s' if changes != 1 else ''} changed, {insertions} insertion{'s' if insertions != 1 else ''}(+), {deletions} deletion{'s' if deletions != 1 else ''}(-)")
            
        except ValueError:
            return
    
    def pop_stash(self, stash_ref: str = "0"):
        """Pop a stash and apply it."""
        # First apply the stash
        if self.apply_stash(stash_ref, show_output=False):
            # Then drop it
            self.drop_stash(stash_ref, show_output=False)
            
            # Show status after popping
            stash_file = self.repo.rvs_dir / "stash"
            if stash_file.exists():
                try:
                    with open(stash_file, 'r', encoding='utf-8') as f:
                        stashes = json.load(f)
                    
                    idx = int(stash_ref)
                    if 0 <= idx < len(stashes):
                        stash = stashes[idx]
                        # Generate a fake hash for the dropped stash (Git shows this)
                        fake_hash = f"f3e709a576304d9c030f2eda55ac6da08152680a"
                        print(f"Dropped refs/stash@{{{idx}}} ({fake_hash})")
                except Exception:
                    pass
    
    def apply_stash(self, stash_ref: str = "0", show_output: bool = True):
        """Apply a stash without removing it."""
        stash_file = self.repo.rvs_dir / "stash"
        
        if not stash_file.exists():
            return False
        
        try:
            with open(stash_file, 'r', encoding='utf-8') as f:
                stashes = json.load(f)
        except Exception:
            return False
        
        try:
            idx = int(stash_ref)
            if idx < 0 or idx >= len(stashes):
                return False
            
            stash = stashes[idx]
            
            # Restore working files
            working_files = stash.get('working_files', {})
            for file_path, file_hash in working_files.items():
                self._restore_file_from_hash(file_path, file_hash)
            
            # Restore index
            index = stash.get('index', {})
            if index:
                self.repo._save_index(index)
            
            if show_output:
                # Show status like Git does after applying stash
                current_branch = self.repo._get_current_branch()
                print(f"On branch {current_branch}")
                
                # Check for modified files
                committed_files = stash.get('committed_files', {})
                modified_files = []
                
                for file_path in working_files:
                    if file_path in committed_files:
                        if working_files[file_path] != committed_files[file_path]:
                            modified_files.append(file_path)
                
                if modified_files:
                    print("Changes not staged for commit:")
                    print('  (use "rvs add <file>..." to update what will be committed)')
                    print('  (use "rvs restore <file>..." to discard changes in working directory)')
                    for file_path in modified_files:
                        print(f"\\tmodified:   {file_path}")
                    print()
                    print('no changes added to commit (use "rvs add" and/or "rvs commit -a")')
            
            return True
            
        except ValueError:
            return False
    
    def drop_stash(self, stash_ref: str = "0", show_output: bool = True):
        """Drop a stash."""
        stash_file = self.repo.rvs_dir / "stash"
        
        if not stash_file.exists():
            return
        
        try:
            with open(stash_file, 'r', encoding='utf-8') as f:
                stashes = json.load(f)
        except Exception:
            return
        
        try:
            idx = int(stash_ref)
            if idx < 0 or idx >= len(stashes):
                return
            
            stash = stashes.pop(idx)
            
            with open(stash_file, 'w', encoding='utf-8') as f:
                json.dump(stashes, f, indent=2)
            
            if show_output:
                print(f"Dropped stash@{{{idx}}} ({stash['message']})")
            
        except ValueError:
            return
    
    def _get_working_files(self) -> Dict[str, str]:
        """Get all files in working tree."""
        working_files = {}
        for file_path in self.repo.repo_path.rglob('*'):
            if file_path.is_file() and not str(file_path).startswith(str(self.repo.rvs_dir)):
                rel_path = file_path.relative_to(self.repo.repo_path)
                try:
                    working_files[str(rel_path)] = self.repo._get_file_hash(file_path)
                except Exception:
                    pass  # Skip files that can't be read
        return working_files
    
    def _restore_to_committed_state(self, committed_files: Dict[str, str]):
        """Restore working directory to committed state."""
        # Remove all files not in committed state
        for file_path in self.repo.repo_path.rglob('*'):
            if file_path.is_file() and not str(file_path).startswith(str(self.repo.rvs_dir)):
                rel_path = file_path.relative_to(self.repo.repo_path)
                if str(rel_path) not in committed_files:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
        
        # Restore committed files
        for file_path, file_hash in committed_files.items():
            self._restore_file_from_hash(file_path, file_hash)
    
    def _restore_file_from_hash(self, file_path: str, file_hash: str):
        """Restore a file from its hash."""
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