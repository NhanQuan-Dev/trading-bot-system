#!/bin/bash
# Format code

echo "Formatting with black..."
black src/

echo "Sorting imports..."
ruff check --select I --fix src/

echo "✓ Formatting complete!"
