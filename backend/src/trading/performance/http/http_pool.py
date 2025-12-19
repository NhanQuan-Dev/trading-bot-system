"""
HTTP Connection Pool with retry and timeout

Usage:
    from shared.performance.http.http_pool import HTTPPool
    
    pool = HTTPPool(max_connections=100)
    response = pool.get("https://api.example.com/data")
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any


class HTTPPool:
    """
    Optimized HTTP client with connection pooling
    
    Features:
    - Connection pooling (reuse connections)
    - Automatic retry on failure
    - Configurable timeouts
    - Thread-safe
    """
    
    def __init__(
        self,
        max_connections: int = 100,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: float = 10.0
    ):
        """
        Initialize HTTP pool
        
        Args:
            max_connections: Max concurrent connections
            max_retries: Number of retry attempts
            backoff_factor: Delay between retries
            timeout: Default request timeout
        """
        self.session = requests.Session()
        self.timeout = timeout
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        # Configure connection pool
        adapter = HTTPAdapter(
            pool_connections=max_connections,
            pool_maxsize=max_connections,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> requests.Response:
        """
        HTTP GET request
        
        Args:
            url: Target URL
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (override default)
            
        Returns:
            Response object
        """
        return self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout or self.timeout
        )
    
    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> requests.Response:
        """
        HTTP POST request
        
        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Response object
        """
        return self.session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout or self.timeout
        )
    
    def close(self):
        """Close session and cleanup connections"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
