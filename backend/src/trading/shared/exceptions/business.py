"""Business exception classes."""


class BusinessException(Exception):
    """Base business exception."""
    pass


class ValidationError(BusinessException):
    """Validation error exception."""
    pass


class NotFoundError(BusinessException):
    """Resource not found exception."""
    pass


class ExchangeConnectionError(BusinessException):
    """Exchange connection error exception."""
    pass


class DuplicateError(BusinessException):
    """Duplicate resource exception."""
    pass


class UnauthorizedError(BusinessException):
    """Unauthorized access exception."""
    pass


class InsufficientBalanceError(BusinessException):
    """Insufficient balance exception."""
    pass


class OrderNotCancellableError(BusinessException):
    """Order cannot be cancelled exception."""
    pass


class RiskLimitExceededError(BusinessException):
    """Risk limit exceeded exception."""
    pass