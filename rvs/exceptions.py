"""
Custom exceptions for RVS.
"""

class RVSError(Exception):
    """Base exception for all RVS errors."""
    pass

class RepositoryError(RVSError):
    """Raised when repository operations fail."""
    pass

class ObjectError(RVSError):
    """Raised when object operations fail."""
    pass

class IndexError(RVSError):
    """Raised when index operations fail."""
    pass

class BranchError(RVSError):
    """Raised when branch operations fail."""
    pass

class MergeError(RVSError):
    """Raised when merge operations fail."""
    pass

class CheckoutError(RVSError):
    """Raised when checkout operations fail."""
    pass
