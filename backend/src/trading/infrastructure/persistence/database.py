"""Database configuration and session management."""
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
import os
from dotenv import load_dotenv

load_dotenv()

# Database URLs
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/trading_platform")
DATABASE_SYNC_URL = os.getenv("DATABASE_SYNC_URL", "postgresql+psycopg2://postgres:password@localhost:5432/trading_platform")

# Create async engine for application use
async_engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("ENABLE_QUERY_LOGGING", "false").lower() == "true",
    pool_size=int(os.getenv("CONNECTION_POOL_SIZE", "20")),
    max_overflow=int(os.getenv("CONNECTION_POOL_MAX_OVERFLOW", "10")),
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create sync engine for migrations
sync_engine = create_engine(
    DATABASE_SYNC_URL,
    echo=False,
    pool_pre_ping=True,
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# For sync operations (migrations, scripts)
def get_sync_db():
    """Get sync database session."""
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Context manager for database operations
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_context():
    """Get database session as context manager (for startup/shutdown operations)."""
    async with AsyncSessionLocal() as session:
        try:
            # logger.info("DEBUG: DB Start Transaction")
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()
