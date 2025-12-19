#!/bin/bash
# Script to manage test database container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

case "$1" in
    start)
        echo "Starting test PostgreSQL database..."
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.test.yml up -d
        echo "Waiting for database to be ready..."
        sleep 5
        docker-compose -f docker-compose.test.yml ps
        echo "✅ Test database is ready at localhost:5433"
        echo "   Database: trading_test"
        echo "   User: test_user"
        echo "   Password: test_password"
        ;;
    
    stop)
        echo "Stopping test PostgreSQL database..."
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.test.yml down
        echo "✅ Test database stopped"
        ;;
    
    restart)
        echo "Restarting test PostgreSQL database..."
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.test.yml down
        docker-compose -f docker-compose.test.yml up -d
        echo "Waiting for database to be ready..."
        sleep 5
        echo "✅ Test database restarted"
        ;;
    
    clean)
        echo "Cleaning test PostgreSQL database (removing volumes)..."
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.test.yml down -v
        echo "✅ Test database cleaned"
        ;;
    
    logs)
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.test.yml logs -f postgres-test
        ;;
    
    psql)
        echo "Connecting to test database..."
        docker exec -it trading-bot-test-db psql -U test_user -d trading_test
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|clean|logs|psql}"
        echo ""
        echo "Commands:"
        echo "  start   - Start test database container"
        echo "  stop    - Stop test database container"
        echo "  restart - Restart test database container"
        echo "  clean   - Stop and remove test database container and volumes"
        echo "  logs    - Show test database logs"
        echo "  psql    - Connect to test database with psql"
        exit 1
        ;;
esac
