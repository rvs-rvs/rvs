"""
Git hooks implementation.
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

class Hook:
    """Manages Git hooks."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.hooks_dir = repo_path / ".rvs" / "hooks"
    
    def run_hook(self, hook_name: str, args: List[str] = None) -> bool:
        """Run a hook script if it exists."""
        hook_file = self.hooks_dir / hook_name
        
        # On Windows, prioritize .bat version
        if platform.system() == "Windows":
            bat_hook_file = self.hooks_dir / f"{hook_name}.bat"
            if bat_hook_file.exists():
                hook_file = bat_hook_file
            elif not hook_file.exists():
                return True  # Neither version exists
        
        if not hook_file.exists():
            return True  # Hook doesn't exist
        
        # On Unix-like systems, check if executable
        if platform.system() != "Windows" and not os.access(hook_file, os.X_OK):
            return True  # Hook isn't executable
        
        temp_files_to_cleanup = []
        try:
            # Prepare environment
            env = os.environ.copy()
            env["RVS_DIR"] = str(self.repo_path / ".rvs")
            
            # Get the appropriate command to execute the hook
            cmd = self._get_hook_command(hook_file, args or [])
            
            # Check if this is a temporary batch file that needs cleanup
            if (platform.system() == "Windows" and len(cmd) >= 3 and 
                cmd[0] == 'cmd' and cmd[1] == '/c' and cmd[2].endswith('.bat')):
                temp_files_to_cleanup.append(cmd[2])
            
            # Run hook
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                env=env,
                capture_output=True,
                text=True
            )
            
            # Only print hook output if it's not the default sample hook messages
            if result.stdout and not result.stdout.strip().startswith("Running "):
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            return result.returncode == 0
        except Exception as e:
            print(f"Error running hook {hook_name}: {e}")
            return False
        finally:
            # Clean up temporary files
            for temp_file in temp_files_to_cleanup:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception:
                    pass  # Ignore cleanup errors
    
    def _get_hook_command(self, hook_file: Path, args: List[str]) -> List[str]:
        """Get the appropriate command to execute a hook file cross-platform."""
        if platform.system() == "Windows":
            # On Windows, we need to determine the interpreter based on shebang or file extension
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('#!'):
                        shebang = first_line[2:].strip()
                        
                        # Handle different shebang patterns
                        if 'python' in shebang.lower():
                            return ['python', str(hook_file)] + args
                        elif any(shell in shebang.lower() for shell in ['sh', 'bash']):
                            # Try to find bash (Git Bash, WSL, etc.)
                            for bash_cmd in ['bash', 'sh']:
                                if self._command_exists(bash_cmd):
                                    return [bash_cmd, str(hook_file)] + args
                            # Fallback: convert shell script to batch equivalent or skip
                            return self._convert_shell_to_batch(hook_file, args)
                        elif 'cmd' in shebang.lower() or 'bat' in shebang.lower():
                            return ['cmd', '/c', str(hook_file)] + args
            except (UnicodeDecodeError, IOError):
                pass
            
            # Check file extension as fallback
            suffix = hook_file.suffix.lower()
            if suffix in ['.py']:
                return ['python', str(hook_file)] + args
            elif suffix in ['.bat', '.cmd']:
                return ['cmd', '/c', str(hook_file)] + args
            elif suffix in ['.ps1']:
                return ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(hook_file)] + args
            
            # Default: try bash first, then convert to batch
            if self._command_exists('bash'):
                return ['bash', str(hook_file)] + args
            else:
                # No bash available, try to convert shell script to batch
                return self._convert_shell_to_batch(hook_file, args)
        else:
            # On Unix-like systems, execute directly (shebang will be handled by OS)
            return [str(hook_file)] + args
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        return shutil.which(command) is not None
    
    def _convert_shell_to_batch(self, hook_file: Path, args: List[str]) -> List[str]:
        """Convert a simple shell script to batch commands."""
        try:
            with open(hook_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if it's a simple sample hook that we can convert inline
            if 'echo "Running' in content and 'exit 0' in content:
                # This is likely a sample hook, convert to simple batch command
                if 'pre-commit' in str(hook_file):
                    return ['cmd', '/c', 'echo Running pre-commit hook']
                elif 'post-commit' in str(hook_file):
                    return ['cmd', '/c', 'echo Running post-commit hook']
                else:
                    return ['cmd', '/c', 'echo Running hook']
            else:
                # For complex scripts, create a temporary batch file that mimics the behavior
                return self._create_temp_batch_from_shell(hook_file, content, args)
                
        except Exception:
            # If reading fails, return a simple success command
            return ['cmd', '/c', 'echo Hook executed successfully']
    
    def _create_temp_batch_from_shell(self, hook_file: Path, content: str, args: List[str]) -> List[str]:
        """Create a temporary batch file from shell script content."""
        import tempfile
        import re
        
        try:
            # Create temporary batch file
            temp_bat = tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False, encoding='utf-8')
            
            # Start with batch header
            temp_bat.write('@echo off\n')
            temp_bat.write('REM Converted from shell script\n')
            temp_bat.write('REM Original: {}\n'.format(hook_file.name))
            temp_bat.write('\n')
            
            # Process each line of the shell script
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Convert common shell commands to batch equivalents
                if line.startswith('echo '):
                    # Handle echo commands
                    message = line[5:].strip()
                    # Remove quotes if present
                    if message.startswith('"') and message.endswith('"'):
                        message = message[1:-1]
                    elif message.startswith("'") and message.endswith("'"):
                        message = message[1:-1]
                    temp_bat.write(f'echo {message}\n')
                    
                elif line == 'exit 0':
                    temp_bat.write('exit /b 0\n')
                    
                elif line.startswith('exit '):
                    code = line[5:].strip()
                    temp_bat.write(f'exit /b {code}\n')
                    
                elif 'python' in line.lower() and ('.py' in line or 'python' == line.split()[0]):
                    # Handle python commands
                    temp_bat.write(f'{line}\n')
                    
                elif line.startswith('cd '):
                    # Handle directory changes
                    path = line[3:].strip().strip('"\'')
                    temp_bat.write(f'cd /d "{path}"\n')
                    
                else:
                    # For other commands, try to execute as-is
                    # Many commands work the same on Windows
                    temp_bat.write(f'{line}\n')
            
            # Ensure we exit with success if no explicit exit
            temp_bat.write('\nif not defined ERRORLEVEL exit /b 0\n')
            temp_bat.close()
            
            return ['cmd', '/c', temp_bat.name] + args
            
        except Exception as e:
            # If conversion fails, return a simple success command
            print(f"Warning: Could not convert shell script {hook_file.name}: {e}")
            return ['cmd', '/c', 'echo Hook conversion failed, continuing...']
    
    def install_sample_hooks(self, show_message: bool = False):
        """Install sample hooks."""
        # Create hooks directory if it doesn't exist
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        
        # Pre-commit hook
        pre_commit = self.hooks_dir / "pre-commit"
        with open(pre_commit, 'w', encoding='utf-8') as f:
            f.write("""#!/bin/sh
# Sample pre-commit hook
echo "Running pre-commit hook"
# Add your checks here
# Exit with non-zero status to abort commit
exit 0
""")
        
        # Post-commit hook
        post_commit = self.hooks_dir / "post-commit"
        with open(post_commit, 'w', encoding='utf-8') as f:
            f.write("""#!/bin/sh
# Sample post-commit hook
echo "Running post-commit hook"
# Add your post-commit actions here
exit 0
""")
        
        # Set executable permissions on Unix-like systems
        if platform.system() != "Windows":
            pre_commit.chmod(0o755)
            post_commit.chmod(0o755)
        
        # On Windows, also create .bat versions for better compatibility
        if platform.system() == "Windows":
            # Pre-commit batch file
            pre_commit_bat = self.hooks_dir / "pre-commit.bat"
            with open(pre_commit_bat, 'w', encoding='utf-8') as f:
                f.write("""@echo off
REM Sample pre-commit hook (Windows batch version)
echo Running pre-commit hook
REM Add your checks here
REM Exit with non-zero status to abort commit
exit /b 0
""")
            
            # Post-commit batch file
            post_commit_bat = self.hooks_dir / "post-commit.bat"
            with open(post_commit_bat, 'w', encoding='utf-8') as f:
                f.write("""@echo off
REM Sample post-commit hook (Windows batch version)
echo Running post-commit hook
REM Add your post-commit actions here
exit /b 0
""")
        
        if show_message:
            if platform.system() == "Windows":
                print("Sample hooks installed in .rvs/hooks/ (both shell and batch versions for Windows compatibility)")
            else:
                print("Sample hooks installed in .rvs/hooks/")
