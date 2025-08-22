# 🚀 RVS - Robust Versioning System

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://python.org)
[![Version](https://img.shields.io/badge/version-2.0.1-green.svg)](https://github.com/rvs-rvs/rvs)
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

## ✨ Features

- 🔧 **Complete Git-like Interface** - Familiar commands and workflows
- 🐍 **Self-Contained Architecture** - Zero external dependencies required
- 📦 **Universal Installation** - Install via pip or run directly on any Python platform
- 🌳 **Full Branching Support** - Create, switch, and merge branches
- 📝 **Staging Area** - Add and commit changes with precision
- 📚 **Commit History** - View and navigate project history
- 🔄 **Advanced Operations** - Rebase, stash, worktree management
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

# Interactive rebase (reapply commits)
rvs rebase main

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

## 🏗️ Architecture

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
  {init,add,commit,status,log,branch,checkout,merge,rebase,restore,rm,ls-files,ls-tree,worktree,stash}
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