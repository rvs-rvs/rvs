# 🚀 RVS - Robust Versioning System

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://python.org)
[![Version](https://img.shields.io/badge/version-2.1.1-green.svg)](https://github.com/rvs-rvs/rvs)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Keywords](https://img.shields.io/badge/keywords-python%20git%20version--control%20python--3%20pypi%20rvs-blue.svg)](#)

**RVS (Robust Versioning System)** brings Git-style version control to environments where traditional solutions fall short. Built entirely in Python, RVS trades execution speed for universal compatibility and deployment simplicity.

**Built for Flexibility**: 
- ✅ Functions in isolated environments (containers, embedded systems, restricted networks)
- ✅ Zero dependency installation
- ✅ Predictable behavior across all Python-supported platforms  
- ✅ Simplified deployment pipeline

**Local-Centric Design**: RVS concentrates on local repository management without remote connectivity features. This focused approach makes it ideal for:
- Offline development workflows
- Edge computing and IoT applications
- Educational and training environments  
- Scenarios with network limitations or security constraints
- Personal project archiving and backup systems

## 🆕 What's New in v2.1.1

**Enhanced Worktree Support**: Complete Git-compatible worktree implementation
- Full worktree lifecycle management (add, list, remove, lock/unlock)
- Git-compatible `.rvs` file structure for seamless interoperability
- Independent HEAD, index, and working directory per worktree

**Detached HEAD Operations**: Comprehensive support for detached HEAD workflows
- Checkout commits directly with `--detach` option
- Create branches from detached HEAD state
- Proper status display and commit operations in detached mode

**New Git Commands**: Extended command set for better Git compatibility
- `rvs show` - Display commit information with multiple output formats
- `rvs diff-tree` - Compare tree objects between commits
- `rvs reset` - Reset HEAD, index, and working tree with `--soft`, `--mixed`, `--hard` modes

**Improved Reliability**: Enhanced error handling and cross-platform compatibility
- Better path normalization for Windows/Linux/macOS
- Robust index state management
- Improved uncommitted changes detection

## ✨ Features

- 🔧 **Complete Git-like Interface** - Familiar commands and workflows
- 🐍 **Self-Contained Architecture** - Zero external dependencies required
- 📦 **Universal Installation** - Install via pip or run directly on any Python platform
- 🌳 **Full Branching Support** - Create, switch, and merge branches with detached HEAD support
- 📝 **Staging Area** - Add and commit changes with precision
- 📚 **Commit History** - View and navigate project history
- 🔄 **Advanced Operations** - Rebase, stash, comprehensive worktree management
- 🏢 **Multi-Worktree Support** - Git-compatible worktree functionality for parallel development
- 🎯 **Detached HEAD Operations** - Full support for detached HEAD workflows
- 🛠️ **Extensible Architecture** - Clean, modular codebase
- 🎯 **Local-First Design** - Focused on local operations without remote dependencies

## 🚀 Quick Start

### Installation

#### From PyPI (Recommended)

```bash
# Install from PyPI
pip install rvs
```

#### From Source

```bash
# Clone the repository
git clone https://github.com/rvs-rvs/rvs.git
cd rvs

# Install using pip
pip install .

# Or install in development mode
pip install -e .
```

### Basic Usage

```bash
# Initialize a new repository
rvs init

# Add files to staging area
rvs add file.txt
rvs add .

# Create a commit
rvs commit -m "Initial commit"

# Check repository status
rvs status

# View commit history
rvs log
```

## 📋 Available Commands

RVS supports all essential local Git operations:

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize a new repository | `rvs init` |
| `add` | Add files to staging area | `rvs add file.txt` |
| `commit` | Create a commit | `rvs commit -m "message"` |
| `status` | Show repository status | `rvs status` |
| `log` | Show commit history | `rvs log` |
| `show` | Display commit information | `rvs show HEAD --name-status` |
| `diff-tree` | Compare tree objects | `rvs diff-tree --name-status -r HEAD` |
| `reset` | Reset HEAD, index, and working tree | `rvs reset --hard HEAD~1` |
| `branch` | List or create branches | `rvs branch feature` |
| `checkout` | Switch branches or restore files | `rvs checkout main` |
| `merge` | Join development histories | `rvs merge feature` |
| `rebase` | Reapply commits on another base | `rvs rebase main` |
| `restore` | Restore working tree files | `rvs restore file.txt` |
| `rm` | Remove files from index/working tree | `rvs rm file.txt` |
| `ls-files` | Show files in index and working tree | `rvs ls-files` |
| `ls-tree` | List contents of tree objects | `rvs ls-tree HEAD` |
| `worktree` | Manage multiple working trees | `rvs worktree add ../feature` |
| `stash` | Stash changes temporarily | `rvs stash` |

## 💡 Usage Examples

### Basic Workflow

```bash
# Start a new project
mkdir my-project && cd my-project
rvs init

# Add some files
echo "Hello World" > hello.txt
rvs add hello.txt
rvs commit -m "Add hello.txt"

# Create and switch to a new branch
rvs branch feature
rvs checkout feature

# Make changes and commit
echo "Feature code" > feature.txt
rvs add feature.txt
rvs commit -m "Add feature"

# Switch back and merge
rvs checkout main
rvs merge feature
```

### Advanced Operations

```bash
# Stash uncommitted changes
rvs stash

# Work with multiple worktrees
rvs worktree add ../hotfix hotfix-branch
rvs worktree list
rvs worktree remove ../hotfix

# Detached HEAD operations
rvs checkout --detach HEAD~2
rvs checkout -b new-feature  # Create branch from detached HEAD

# Reset operations
rvs reset --soft HEAD~1      # Reset HEAD only
rvs reset --mixed HEAD~1     # Reset HEAD and index (default)
rvs reset --hard HEAD~1      # Reset HEAD, index, and working tree

# Interactive rebase (reapply commits)
rvs rebase main

# Show commit details
rvs show HEAD --name-status  # Show files changed in commit
rvs show HEAD --stat         # Show diffstat

# Restore specific files from a commit
rvs restore --source=HEAD~1 file.txt
```

### Repository Management

```bash
# Check what's staged and unstaged
rvs status

# View detailed commit history
rvs log --oneline

# List all files tracked by RVS
rvs ls-files

# Examine tree structure
rvs ls-tree HEAD
```

## 🏢 Worktree Management

RVS provides comprehensive Git-compatible worktree functionality, allowing you to work on multiple branches simultaneously:

### Creating and Managing Worktrees

```bash
# Create a new worktree for a feature branch
rvs worktree add ../feature-branch feature

# Create a worktree in detached HEAD state
rvs worktree add ../hotfix HEAD~2

# List all worktrees
rvs worktree list
# Output:
# /path/to/main/repo    abc1234 [main]
# /path/to/feature      def5678 [feature]
# /path/to/hotfix       ghi9012 (detached HEAD)

# Remove a worktree
rvs worktree remove ../feature-branch

# Lock/unlock worktrees
rvs worktree lock ../feature-branch
rvs worktree unlock ../feature-branch
```

### Worktree Benefits

- **Parallel Development**: Work on multiple features simultaneously
- **Git Compatibility**: Uses the same `.rvs` file structure as Git worktrees
- **Independent State**: Each worktree has its own HEAD, index, and working directory
- **Shared History**: All worktrees share the same commit history and branches
- **Detached HEAD Support**: Create worktrees in detached HEAD state for experimental work

### Detached HEAD Workflows

RVS fully supports detached HEAD operations for experimental development:

```bash
# Enter detached HEAD state
rvs checkout --detach HEAD~3

# Make experimental changes
echo "experimental feature" > experiment.txt
rvs add experiment.txt
rvs commit -m "Experimental feature"

# Create a branch from detached HEAD
rvs checkout -b experiment-branch

# Or return to a branch, leaving experimental commits
rvs checkout main
```

## 🏧 Architecture

RVS is built with a robust, modular architecture designed for reliability and portability:

```
rvs/
├── core/           # Core functionality
│   ├── repository.py   # Repository management
│   ├── objects.py      # Git object handling
│   ├── index.py        # Staging area
│   ├── refs.py         # Branch/tag references
│   └── hooks.py        # Hook system
├── commands/       # Command implementations
│   ├── add.py          # Add command
│   ├── commit.py       # Commit command
│   ├── branch.py       # Branch operations
│   └── ...             # Other commands
├── cli.py          # Command-line interface
└── exceptions.py   # Custom exceptions
```

## 🔧 Command Line Options

```bash
usage: rvs [-h] [--repo REPO] [--version] {command} ...

RVS - Robust Versioning System

positional arguments:
  {init,add,commit,status,log,show,diff-tree,reset,branch,checkout,merge,rebase,restore,rm,ls-files,ls-tree,worktree,stash}
                        Available commands

options:
  -h, --help            Show help message and exit
  --repo REPO           Repository path (default: current directory)
  --version             Show program's version number and exit
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** and add tests
4. **Commit your changes** (`git commit -m 'Add amazing feature'`)
5. **Push to the branch** (`git push origin feature/amazing-feature`)
6. **Open a Pull Request**

### Development Setup

```bash
# Clone the repository
git clone https://github.com/rvs-rvs/rvs.git
cd rvs

# Install in development mode
pip install -e .

# Run tests (if available)
python -m pytest

# Run RVS directly
python -m rvs --help
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by Git's elegant design and powerful functionality
- Built with Python's excellent standard library
- Thanks to the open-source community for inspiration and feedback

## 📞 Contact

- **Project**: [rvs-rvs/rvs](https://github.com/rvs-rvs/rvs)
- **Issues**: [GitHub Issues](https://github.com/rvs-rvs/rvs/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rvs-rvs/rvs/discussions)

---

<div align="center">

**⭐ Star this repository if you find it useful! ⭐**

Made with ❤️ for robust, portable version control

</div>