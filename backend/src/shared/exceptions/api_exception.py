class APIException(Exception):
    """Custom exception for API-related errors."""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

    def __str__(self):
        return f"APIException: {self.args[0]} (Status Code: {self.status_code})"

# Alias for backward compatibility
ApiException = APIException