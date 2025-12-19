#!/usr/bin/env python3
"""
Comprehensive script to fix all absolute trading imports to relative imports.
"""
import os
import re

# Define the patterns and their replacements based on file location
IMPORT_REPLACEMENTS = {
    # From interfaces/repositories
    'src/trading/interfaces/repositories/': {
        'from trading.domain.': 'from ...domain.',
        'from trading.infrastructure.': 'from ...infrastructure.',
        'from trading.shared.': 'from ...shared.',
    },
    # From infrastructure/persistence/repositories
    'src/trading/infrastructure/persistence/repositories/': {
        'from trading.domain.': 'from ....domain.',
        'from trading.infrastructure.': 'from ....',
        'from trading.shared.': 'from ....shared.',
    },
    # From infrastructure/jobs
    'src/trading/infrastructure/jobs/': {
        'from trading.domain.': 'from ...domain.',
        'from trading.application.': 'from ...application.',
        'from trading.infrastructure.': 'from ..',
        'from trading.shared.': 'from ...shared.',
    },
    # From application/schemas
    'src/trading/application/schemas/': {
        'from trading.domain.': 'from ...domain.',
        'from trading.shared.': 'from ...shared.',
    },
    # From application/use_cases/order
    'src/trading/application/use_cases/order/': {
        'from trading.domain.': 'from ....domain.',
        'from trading.application.': 'from ...',
        'from trading.infrastructure.': 'from ....infrastructure.',
        'from trading.shared.': 'from ....shared.',
    },
    # From presentation/controllers
    'src/trading/presentation/controllers/': {
        'from trading.domain.': 'from ...domain.',
        'from trading.application.': 'from ...application.',
        'from trading.shared.': 'from ...shared.',
    },
}

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Find the appropriate replacement pattern
        for dir_pattern, replacements in IMPORT_REPLACEMENTS.items():
            if dir_pattern in file_path:
                for old_pattern, new_pattern in replacements.items():
                    content = content.replace(old_pattern, new_pattern)
                break
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed {file_path}")
            return True
        else:
            print(f"ℹ️ No changes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix all imports."""
    files_to_fix = [
        'src/trading/interfaces/repositories/exchange_repository.py',
        'src/trading/infrastructure/persistence/repositories/bot_repository.py',
        'src/trading/infrastructure/jobs/tasks.py',
        'src/trading/application/schemas/order_schemas.py',
        'src/trading/application/use_cases/order/create_order.py',
        'src/trading/application/use_cases/order/cancel_order.py',
        'src/trading/application/use_cases/order/get_order_by_id.py',
        'src/trading/application/use_cases/order/get_orders.py',
        'src/trading/application/use_cases/order/update_order_status.py',
        'src/trading/presentation/controllers/order_controller.py',
    ]
    
    fixed_count = 0
    total_count = len(files_to_fix)
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_imports_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️ File not found: {file_path}")
    
    print(f"\n📊 Summary: Fixed {fixed_count}/{total_count} files")

if __name__ == '__main__':
    main()