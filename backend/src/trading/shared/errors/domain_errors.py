"""
Domain layer errors
"""


class DomainError(Exception):
    """Base exception for domain errors"""
    pass


class InvalidOperationError(DomainError):
    """Raised when an invalid operation is attempted"""
    pass


class BusinessRuleViolationError(DomainError):
    """Raised when a business rule is violated"""
    pass


class AggregateNotFoundError(DomainError):
    """Raised when an aggregate is not found"""
    pass


class InvariantViolationError(DomainError):
    """Raised when an invariant is violated"""
    pass


class InsufficientBalanceError(DomainError):
    """Raised when balance is insufficient for an operation"""
    pass


class PositionNotFoundError(DomainError):
    """Raised when a position is not found"""
    pass


class DuplicatePositionError(DomainError):
    """Raised when attempting to create duplicate position"""
    pass
