"""
Base command class for RVS commands.
"""
from abc import ABC, abstractmethod
from argparse import ArgumentParser, _SubParsersAction
from typing import Any
from ..core.repository import RVS

class BaseCommand(ABC):
    """Base class for all RVS commands."""
    
    def __init__(self, repository: RVS):
        self.repo = repository
    
    @classmethod
    @abstractmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register command parser with subparsers."""
        pass
    
    @abstractmethod
    def execute_from_args(self, args: Any) -> None:
        """Execute command from parsed arguments."""
        pass
