"""
Application layer errors
"""


class ApplicationError(Exception):
    """Base exception for application errors"""
    pass


class UseCaseExecutionError(ApplicationError):
    """Raised when a use case fails to execute"""
    pass


class ValidationError(ApplicationError):
    """Raised when input validation fails"""
    pass


class AuthorizationError(ApplicationError):
    """Raised when authorization fails"""
    pass


class ResourceNotFoundError(ApplicationError):
    """Raised when a resource is not found"""
    pass
