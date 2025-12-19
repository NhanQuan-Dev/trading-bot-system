"""
Infrastructure layer errors
"""


class InfrastructureError(Exception):
    """Base exception for infrastructure errors"""
    pass


class DatabaseError(InfrastructureError):
    """Raised when database operations fail"""
    pass


class NetworkError(InfrastructureError):
    """Raised when network operations fail"""
    pass


class ExternalAPIError(InfrastructureError):
    """Raised when external API calls fail"""
    pass


class CacheError(InfrastructureError):
    """Raised when cache operations fail"""
    pass


class ConfigurationError(InfrastructureError):
    """Raised when configuration is invalid"""
    pass
