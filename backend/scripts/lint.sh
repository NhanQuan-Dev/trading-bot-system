#!/bin/bash
# Run linters

echo "Running ruff..."
ruff check src/

echo "Running mypy..."
mypy src/

echo "Running black (check only)..."
black --check src/

echo "✓ Linting complete!"
