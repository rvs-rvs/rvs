"""
Add command implementation.
"""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List
from .base import BaseCommand

class AddCommand(BaseCommand):
    """Add files to the staging area."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register add command parser."""
        parser = subparsers.add_parser(
            "add",
            help="Add files to staging area"
        )
        parser.add_argument(
            "files", 
            nargs="+", 
            help="Files or directories to add"
        )
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute add command from parsed arguments."""
        self.execute(args.files)
    
    def execute(self, files: List[str]) -> None:
        """Add files to staging area."""
        self.repo.add(files)
