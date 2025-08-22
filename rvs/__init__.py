"""
RVS - Robust Versioning System
Git-style version control built for universal compatibility and deployment simplicity.
"""
__version__ = "2.1.1"
__author__ = "RVS"
__description__ = "Robust Versioning System - Git-style version control built for universal compatibility"
from .core.repository import RVS
from .exceptions import RVSError, RepositoryError, ObjectError
__all__ = [
    "RVS",
    "RVSError", 
    "RepositoryError",
    "ObjectError",
    "__version__"
]
