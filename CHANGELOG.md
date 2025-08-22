# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-08-21

### 🎉 Major Features Added

#### Git-like Worktree Implementation
- **Complete Worktree Support**: Implemented full Git-compatible worktree functionality
  - `rvs worktree add <path> <commit>` - Create new worktrees
  - `rvs worktree list` - List all worktrees
  - `rvs worktree remove <path>` - Remove worktrees
  - `rvs worktree lock/unlock <path>` - Lock/unlock worktrees
- **Git-compatible File Structure**: 
  - Worktrees now use `.rvs` **file** (not directory) containing `rvsdir: /path/to/metadata`
  - Metadata stored in main repo at `.rvs/worktrees/worktree-name/`
  - Exactly matches Git's worktree behavior

#### New Git Commands
- **`rvs show`**: Display commit information with multiple output formats
  - `rvs show <commit> --name-status` - Show file changes with status
  - `rvs show <commit> --name-only` - Show only changed file names
  - `rvs show <commit> --stat` - Show diffstat information
- **`rvs diff-tree`**: Compare tree objects
  - `rvs diff-tree --no-commit-id --name-status -r <commit>` - Git-compatible tree comparison
  - Support for comparing commits with their parents
- **`rvs reset`**: Reset HEAD, index, and working tree
  - `rvs reset --soft <commit>` - Reset only HEAD
  - `rvs reset --mixed <commit>` - Reset HEAD and index (default)
  - `rvs reset --hard <commit>` - Reset HEAD, index, and working tree
  - `rvs reset HEAD~<n>` - Support for ancestor commit syntax

#### Enhanced Checkout Command
- **Branch Creation**: `rvs checkout -b <branch>` - Create and switch to new branch
- **Force Branch Creation**: `rvs checkout -B <branch>` - Create/reset and switch to branch
- **Detached HEAD**: `rvs checkout --detach <commit>` - Checkout in detached HEAD state
- **Path Checkout**: `rvs checkout <commit> -- <files>` - Checkout specific files

### 🔧 Technical Improvements

#### Path Normalization
- **Cross-platform Compatibility**: Fixed file path handling for Windows/Linux/macOS
- **Git-like Path Handling**: 
  - `./example.txt` now correctly normalizes to `example.txt`
  - Eliminates duplicate file entries in status output
  - Consistent forward-slash usage across platforms
- **Relative Path Resolution**: Properly handles complex paths like `./subdir/../file.txt`

#### Worktree Infrastructure
- **Repository Detection**: Automatically detects worktrees vs main repositories
- **Index Management**: Separate index files for each worktree
- **HEAD Management**: Independent HEAD pointers for each worktree
- **Status Command**: Full worktree support with correct branch detection

#### Code Quality
- **Error Handling**: Improved error messages and edge case handling
- **File Operations**: Robust file cleanup and restoration
- **Cross-platform**: Consistent behavior across operating systems

### 🎯 Git Compatibility

#### Command Parity
All new commands produce output identical to Git:
- Status indicators (A, M, D) match Git format
- Error messages sent to stderr appropriately
- Success messages formatted like Git
- Command-line arguments and options match Git syntax

#### Workflow Support
- **Detached HEAD Workflows**: Full support for detached HEAD operations
- **Branch Management**: Create branches from any commit or detached HEAD
- **File Operations**: Checkout, reset, and restore operations work identically to Git
- **Multi-worktree Development**: Complete support for multiple working directories

### 📦 Version Update
- **Version Bump**: Updated from 2.0.3 to 2.1.0
- **PyPI Compatibility**: Ready for automatic publishing via GitHub Actions

### 🐛 Bug Fixes
- Fixed `.rvs` file being removed during checkout operations
- Corrected worktree status showing "No commits yet" in detached HEAD
- Resolved path normalization issues causing duplicate file entries
- Fixed index loading/saving in worktree environments

### 🔄 Breaking Changes
- Worktree `.rvs` structure changed from directory to file (automatic migration)
- Path normalization may affect scripts relying on non-normalized paths

---

## [2.0.3] - Previous Release
- Comprehensive 'rvs diff' command with Git-like behavior
- GitHub Actions workflows for PyPI publishing and build testing
- Comprehensive publishing documentation

---

*For older versions, see git history or previous releases.*