# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [1.0.0] - 2025-12-17

### Added
- Initial production release
- User authentication and authorization (JWT-based)
- Exchange connection management (Binance USDM Futures)
- Trading bot creation and management
- Strategy system with custom Python code execution
- Backtesting engine with historical data
- WebSocket real-time market data streams
- Risk management system with alerts
- Redis caching and job queue
- PostgreSQL database with Alembic migrations
- Comprehensive API documentation
- 108 integration tests with 100% pass rate
- Docker containerization
- Frontend with React + TypeScript + Vite

### Technical Details
- Python 3.12.3 backend with FastAPI
- PostgreSQL 16 database
- Redis 7.0 for caching
- SQLAlchemy 2.0 with async support
- Domain-Driven Design architecture
- RESTful API with OpenAPI documentation

---

## How to Update This File

When creating a new release:

1. Move items from `[Unreleased]` to new version section
2. Add version number and date: `## [X.Y.Z] - YYYY-MM-DD`
3. Group changes by type:
   - **Added**: New features
   - **Changed**: Changes to existing functionality
   - **Deprecated**: Soon-to-be removed features
   - **Removed**: Removed features
   - **Fixed**: Bug fixes
   - **Security**: Security fixes

### Example:

```markdown
## [1.1.0] - 2025-12-20

### Added
- Multi-exchange support for Bybit
- Advanced order types (OCO, Trailing Stop)
- Performance analytics dashboard

### Changed
- Improved WebSocket reconnection logic
- Optimized backtest execution speed

### Fixed
- Fixed timezone handling in user profiles
- Corrected balance calculation for margin accounts

### Security
- Updated JWT token expiration to 24 hours
- Added rate limiting to API endpoints
```
