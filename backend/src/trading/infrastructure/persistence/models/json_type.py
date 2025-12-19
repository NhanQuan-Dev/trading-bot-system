"""Cross-database JSON type that works with both PostgreSQL and SQLite."""
from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql


def get_json_type(engine_name: str = None):
    """Return JSON type for PostgreSQL (JSONB) or generic JSON for others.
    
    Args:
        engine_name: Database engine name. If 'postgresql', returns JSONB.
    
    Returns:
        JSONB for PostgreSQL, JSON for others
    """
    if engine_name == 'postgresql':
        return postgresql.JSONB
    return JSON


# Use this as a drop-in replacement for JSONB
# It will use JSONB for PostgreSQL and JSON for SQLite/others
JSONBType = JSON  # Default to JSON which works everywhere
