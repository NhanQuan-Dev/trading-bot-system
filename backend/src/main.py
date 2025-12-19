"""Main entry point for the trading bot platform."""
import uvicorn
from trading.app import app


def create_app():
    """Create application for testing."""
    return app


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )