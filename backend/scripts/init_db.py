#!/usr/bin/env python3
"""
Initialize database schema and tables
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading.infrastructure.persistence.database import init_db, create_tables


def main():
    print("Initializing database...")
    
    # Initialize database connection
    init_db()
    
    # Create all tables
    create_tables()
    
    print("✓ Database initialized successfully!")


if __name__ == "__main__":
    main()
