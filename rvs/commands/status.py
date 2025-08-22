"""
Status command implementation.
"""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from .base import BaseCommand

class StatusCommand(BaseCommand):
    """Show repository status."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register status command parser."""
        parser = subparsers.add_parser(
            "status",
            help="Show repository status"
        )
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute status command from parsed arguments."""
        self.execute()
    
    def execute(self) -> None:
        """Show repository status."""
        self.repo.status()
