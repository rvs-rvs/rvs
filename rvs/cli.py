"""
Command Line Interface for RVS.
"""
import argparse
import sys
from typing import List, Optional
from .core.repository import RVS
from .commands import (
    InitCommand, AddCommand, CommitCommand, StatusCommand,
    LogCommand, BranchCommand, CheckoutCommand, MergeCommand,
    RebaseCommand, RestoreCommand, RmCommand, LsFilesCommand,
    LsTreeCommand, WorktreeCommand, StashCommand, DiffCommand,
    ShowCommand, DiffTreeCommand, ResetCommand
)
from .exceptions import RVSError

def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description="RVS - Robust Versioning System",
        prog="rvs"
    )
    parser.add_argument(
        "--repo", 
        default=".", 
        help="Repository path (default: current directory)"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"%(prog)s {__import__('rvs').__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Register all commands
    InitCommand.register_parser(subparsers)
    AddCommand.register_parser(subparsers)
    CommitCommand.register_parser(subparsers)
    StatusCommand.register_parser(subparsers)
    LogCommand.register_parser(subparsers)
    BranchCommand.register_parser(subparsers)
    CheckoutCommand.register_parser(subparsers)
    MergeCommand.register_parser(subparsers)
    RebaseCommand.register_parser(subparsers)
    RestoreCommand.register_parser(subparsers)
    RmCommand.register_parser(subparsers)
    LsFilesCommand.register_parser(subparsers)
    LsTreeCommand.register_parser(subparsers)
    WorktreeCommand.register_parser(subparsers)
    StashCommand.register_parser(subparsers)
    DiffCommand.register_parser(subparsers)
    ShowCommand.register_parser(subparsers)
    DiffTreeCommand.register_parser(subparsers)
    ResetCommand.register_parser(subparsers)
    
    return parser

def handle_checkout_with_separator():
    """Handle checkout command with -- separator for files."""
    try:
        # Find the -- separator
        separator_index = sys.argv.index("--")
        
        # Parse arguments
        repo_path = "."
        if "--repo" in sys.argv[:separator_index]:
            repo_index = sys.argv.index("--repo")
            if repo_index + 1 < separator_index:
                repo_path = sys.argv[repo_index + 1]
        
        # Get target (commit/branch) - should be right after "checkout"
        target = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--repo" else None
        if not target or target.startswith("--"):
            print("fatal: missing target commit/branch")
            sys.exit(1)
        
        # Get files after --
        files = sys.argv[separator_index + 1:]
        if not files:
            print("fatal: no files specified after --")
            sys.exit(1)
        
        # Execute checkout
        rvs = RVS(repo_path)
        checkout_cmd = CheckoutCommand(rvs)
        checkout_cmd.execute(target, files)
        
    except ValueError:
        print("fatal: -- separator not found")
        sys.exit(1)
    except RVSError as e:
        print(f"fatal: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"fatal: unexpected error: {e}")
        sys.exit(1)

def main():
    """Main CLI entry point."""
    # Handle special case for checkout with -- separator
    if len(sys.argv) > 1 and sys.argv[1] == "checkout" and "--" in sys.argv:
        handle_checkout_with_separator()
        return
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Create repository instance
        rvs = RVS(args.repo)
        
        # Execute the appropriate command
        command_map = {
            "init": InitCommand,
            "add": AddCommand,
            "commit": CommitCommand,
            "status": StatusCommand,
            "log": LogCommand,
            "branch": BranchCommand,
            "checkout": CheckoutCommand,
            "merge": MergeCommand,
            "rebase": RebaseCommand,
            "restore": RestoreCommand,
            "rm": RmCommand,
            "ls-files": LsFilesCommand,
            "ls-tree": LsTreeCommand,
            "worktree": WorktreeCommand,
            "stash": StashCommand,
            "diff": DiffCommand,
            "show": ShowCommand,
            "diff-tree": DiffTreeCommand,
            "reset": ResetCommand,
        }
        
        command_class = command_map.get(args.command)
        if command_class:
            command = command_class(rvs)
            command.execute_from_args(args)
        else:
            print(f"fatal: unknown command '{args.command}'")
            sys.exit(1)
    
    except RVSError as e:
        print(f"fatal: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print(f"fatal: unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
