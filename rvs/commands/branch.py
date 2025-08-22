"""Branch command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from .base import BaseCommand

class BranchCommand(BaseCommand):
    """List or create branches."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register branch command parser."""
        parser = subparsers.add_parser('branch', help='List or create branches')
        parser.add_argument("name", nargs="?", help="Branch name to create")
        parser.add_argument("-l", "--list", action="store_true", help="List branches")
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute branch command from parsed arguments."""
        self.execute(args.name, args.list)
    
    def execute(self, branch_name: str = None, list_branches: bool = False) -> None:
        """List or create branches."""
        self.repo.branch(branch_name, list_branches)
