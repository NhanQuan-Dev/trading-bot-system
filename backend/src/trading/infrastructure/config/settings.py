"""Application settings."""
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    
    # Environment
    ENVIRONMENT: str = "development"
    APP_ENV: str = "development"  # Alias for ENVIRONMENT
    DEBUG: bool = True
    
    # Application
    APP_NAME: str = "Trading Bot Platform"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "dev-fernet-key-change-in-production")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres123@localhost:5432/trading_platform"
    )
    DATABASE_SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL",
        "postgresql://postgres:postgres123@localhost:5432/trading_platform"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    ENABLE_QUERY_LOGGING: bool = False
    CONNECTION_POOL_SIZE: int = 20
    CONNECTION_POOL_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    REDIS_CACHE_TTL: int = 300  # 5 minutes
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080,http://localhost:8081,http://127.0.0.1:8081"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # API Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # Exchange API
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")  # Alias
    BINANCE_TESTNET: bool = True
    BINANCE_BASE_URL: str = "https://testnet.binancefuture.com"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_MAX_CONNECTIONS: int = 1000
    
    # Performance
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 100
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore'


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
