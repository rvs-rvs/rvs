"""Commit command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from .base import BaseCommand

class CommitCommand(BaseCommand):
    """Create a commit."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register commit command parser."""
        parser = subparsers.add_parser("commit", help="Create a commit")
        parser.add_argument("-m", "--message", required=True, help="Commit message")
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute commit command from parsed arguments."""
        self.execute(args.message)
    
    def execute(self, message: str) -> None:
        """Create a commit."""
        self.repo.commit(message)
