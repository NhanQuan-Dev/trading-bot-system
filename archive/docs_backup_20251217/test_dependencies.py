"""Test script to validate dependency injection setup."""
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from trading.infrastructure.persistence.database import AsyncSessionLocal
    
    # Test simple imports first
    from trading.infrastructure.persistence.repositories.bot_repository import BotRepository, StrategyRepository
    print("✓ Repository imports work")
    
    from trading.interfaces.dependencies.providers import (
        get_bot_repository,
        get_strategy_repository,
        get_candle_repository,
        get_create_bot_use_case,
        get_get_bots_use_case
    )
    print("✓ Dependency provider imports work")

except Exception as e:
    print(f"❌ Import test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_dependency_injection():
    """Test that all dependency providers work correctly."""
    async with AsyncSessionLocal() as session:
        try:
            print("Testing dependency injection...")
            
            # Test repository providers
            bot_repo = await get_bot_repository(session)
            strategy_repo = await get_strategy_repository(session)
            candle_repo = await get_candle_repository(session)
            
            print("✓ Repository providers work")
            
            # Test use case providers
            create_bot_use_case = await get_create_bot_use_case(bot_repo)
            get_bots_use_case = await get_get_bots_use_case(bot_repo)
            
            print("✓ Use case providers work")
            
            print("✅ All dependency injection tests passed!")
            
        except Exception as e:
            print(f"❌ Dependency injection test failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_dependency_injection())