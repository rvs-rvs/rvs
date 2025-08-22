"""
Init command implementation.
"""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from .base import BaseCommand

class InitCommand(BaseCommand):
    """Initialize a new RVS repository."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register init command parser."""
        parser = subparsers.add_parser(
            "init",
            help="Initialize a new repository"
        )
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute init command from parsed arguments."""
        self.execute()
    
    def execute(self) -> None:
        """Initialize a new repository."""
        self.repo.init()
