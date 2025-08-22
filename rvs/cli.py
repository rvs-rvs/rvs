"""
Command Line Interface for RVS.
"""
import argparse
import sys
from typing import List, Optional
from .core.repository import RVS

class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that suppresses subcommand help in main help."""
    def _format_action(self, action):
        # Skip subparsers action to avoid showing individual command help
        if isinstance(action, argparse._SubParsersAction):
            return ''
        return super()._format_action(action)
from .commands import (
    InitCommand, AddCommand, CommitCommand, StatusCommand,
    LogCommand, BranchCommand, CheckoutCommand, SwitchCommand, MergeCommand,
    RebaseCommand, RestoreCommand, RmCommand, MvCommand, LsFilesCommand,
    LsTreeCommand, WorktreeCommand, StashCommand, DiffCommand,
    ShowCommand, DiffTreeCommand, ResetCommand
)
from .exceptions import RVSError

def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description="RVS - Robust Versioning System",
        prog="rvs",
        formatter_class=CustomHelpFormatter,
        epilog="""These are common RVS commands used in various situations:

start a working area
   init      Create an empty RVS repository or reinitialize an existing one

work on the current change
   add       Add file contents to the index
   mv        Move or rename a file, a directory, or a symlink
   restore   Restore working tree files
   rm        Remove files from the working tree and from the index

examine the history and state
   diff      Show changes between commits, commit and working tree, etc
   log       Show commit logs
   show      Show various types of objects
   status    Show the working tree status

grow, mark and tweak your common history
   branch    List, create, or delete branches
   checkout  Switch branches or restore working tree files
   commit    Record changes to the repository
   merge     Join two or more development histories together
   rebase    Reapply commits on top of another base tip
   reset     Reset current HEAD to the specified state
   switch    Switch branches

low-level commands / interrogators
   diff-tree Compare trees
   ls-files  Show information about files in the index and working tree
   ls-tree   List the contents of a tree object
   stash     Stash changes in a dirty working directory
   worktree  Manage multiple working trees

See 'rvs <command> --help' to read about a specific command."""
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
    
    subparsers = parser.add_subparsers(
        dest="command", 
        help="RVS command to run (see command list below)",
        metavar="<command>"
    )
    
    # Register all commands
    InitCommand.register_parser(subparsers)
    AddCommand.register_parser(subparsers)
    CommitCommand.register_parser(subparsers)
    StatusCommand.register_parser(subparsers)
    LogCommand.register_parser(subparsers)
    BranchCommand.register_parser(subparsers)
    CheckoutCommand.register_parser(subparsers)
    SwitchCommand.register_parser(subparsers)
    MergeCommand.register_parser(subparsers)
    RebaseCommand.register_parser(subparsers)
    RestoreCommand.register_parser(subparsers)
    RmCommand.register_parser(subparsers)
    MvCommand.register_parser(subparsers)
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
            "switch": SwitchCommand,
            "merge": MergeCommand,
            "rebase": RebaseCommand,
            "restore": RestoreCommand,
            "rm": RmCommand,
            "mv": MvCommand,
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
