#!/bin/bash
# Verification script to check if everything is set up correctly

echo "════════════════════════════════════════════════"
echo "  Trading Bot Platform - System Check"
echo "════════════════════════════════════════════════"
echo ""

ERRORS=0

# Check Python version
echo -n "✓ Checking Python version... "
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
    echo "✓ $PYTHON_VERSION"
else
    echo "✗ Python 3.12+ required (found $PYTHON_VERSION)"
    ERRORS=$((ERRORS + 1))
fi

# Check virtual environment
echo -n "✓ Checking virtual environment... "
if [ -d "venv" ]; then
    echo "✓ exists"
else
    echo "⚠ not found (will be created on first run)"
fi

# Check .env file
echo -n "✓ Checking .env configuration... "
if [ -f ".env" ]; then
    echo "✓ exists"
    
    # Check required environment variables
    source .env
    if [ -z "$DATABASE_URL" ]; then
        echo "  ⚠ WARNING: DATABASE_URL not set in .env"
    fi
    if [ -z "$REDIS_URL" ]; then
        echo "  ⚠ WARNING: REDIS_URL not set in .env"
    fi
else
    echo "✗ missing"
    echo "  Run: cp .env.example .env"
    ERRORS=$((ERRORS + 1))
fi

# Check requirements.txt
echo -n "✓ Checking requirements.txt... "
if [ -f "requirements.txt" ]; then
    echo "✓ exists"
else
    echo "✗ missing"
    ERRORS=$((ERRORS + 1))
fi

# Check source files
echo -n "✓ Checking source structure... "
REQUIRED_FILES=(
    "src/main.py"
    "src/domain/entities/__init__.py"
    "src/application/services/__init__.py"
    "src/infrastructure/database/connection.py"
    "src/presentation/controllers/__init__.py"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        if [ $MISSING_FILES -eq 0 ]; then
            echo ""
        fi
        echo "  ✗ Missing: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -eq 0 ]; then
    echo "✓ all files present"
else
    ERRORS=$((ERRORS + 1))
fi

# Test imports (if venv exists)
if [ -d "venv" ]; then
    echo -n "✓ Testing Python imports... "
    source venv/bin/activate 2>/dev/null
    
    if python3 -c "
try:
    import fastapi
    import sqlalchemy
    import redis
    import pydantic
    exit(0)
except Exception as e:
    print(str(e))
    exit(1)
" 2>/dev/null; then
        echo "✓ all imports OK"
    else
        echo "✗ import errors detected"
        echo "  Run: pip install -r requirements.txt"
        ERRORS=$((ERRORS + 1))
    fi
    
    deactivate 2>/dev/null
fi

# Check database connection (optional)
if [ -f ".env" ]; then
    echo -n "✓ Testing database connection... "
    source .env
    if [ -n "$DATABASE_URL" ]; then
        # Simple connection test would go here
        echo "⚠ skipped (manual check recommended)"
    else
        echo "⚠ DATABASE_URL not configured"
    fi
fi

# Check Redis connection (optional)
if [ -f ".env" ]; then
    echo -n "✓ Testing Redis connection... "
    source .env
    if [ -n "$REDIS_URL" ]; then
        # Simple connection test would go here
        echo "⚠ skipped (manual check recommended)"
    else
        echo "⚠ REDIS_URL not configured"
    fi
fi

echo ""
echo "════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ]; then
    echo "✓✓✓ ALL CHECKS PASSED ✓✓✓"
    echo ""
    echo "Ready to run! Execute: ./run.sh"
    exit 0
else
    echo "✗✗✗ FOUND $ERRORS ERROR(S) ✗✗✗"
    echo ""
    echo "Please fix the errors above before running."
    exit 1
fi
