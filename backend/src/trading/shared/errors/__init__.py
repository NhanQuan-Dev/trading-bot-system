"""
Error classes
"""

from .domain_errors import (
    DomainError,
    InvalidOperationError,
    BusinessRuleViolationError,
    AggregateNotFoundError,
    InvariantViolationError,
)

from .application_errors import (
    ApplicationError,
    UseCaseExecutionError,
    ValidationError,
    AuthorizationError,
    ResourceNotFoundError,
)

from .infrastructure_errors import (
    InfrastructureError,
    DatabaseError,
    NetworkError,
    ExternalAPIError,
    CacheError,
    ConfigurationError,
)

__all__ = [
    # Domain
    "DomainError",
    "InvalidOperationError",
    "BusinessRuleViolationError",
    "AggregateNotFoundError",
    "InvariantViolationError",
    # Application
    "ApplicationError",
    "UseCaseExecutionError",
    "ValidationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    # Infrastructure
    "InfrastructureError",
    "DatabaseError",
    "NetworkError",
    "ExternalAPIError",
    "CacheError",
    "ConfigurationError",
]
