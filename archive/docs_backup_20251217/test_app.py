#!/usr/bin/env python3
"""Test FastAPI app creation."""

try:
    from src.trading.app import create_app
    app = create_app()
    print("✅ FastAPI app created successfully!")
    print(f"App title: {app.title}")
    print(f"Number of routes: {len(app.routes)}")
except Exception as e:
    print(f"❌ Failed to create app: {e}")
    import traceback
    traceback.print_exc()