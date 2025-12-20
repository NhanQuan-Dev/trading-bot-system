from fastapi import APIRouter, HTTPException
from typing import List, Any

# Import seed strategies for proper UUIDs
from ....infrastructure.persistence.seed_strategies import STRATEGIES

router = APIRouter()

@router.get("", response_model=List[Any])
async def get_strategies():
    """
    Get a list of all available trading strategies.
    
    Returns:
        List of strategy objects with proper UUIDs for backtesting.
    """
    return [
        {
            "id": str(s["id"]),
            "name": s["name"],
            "type": s["strategy_type"],
            "description": s["description"],
            # Mock stats for UI display
            "status": "inactive",
            "activeBots": 0,
            "totalTrades": 0,
            "winRate": 0,
            "avgPnl": 0,
            "totalPnl": 0,
            "sharpeRatio": 0,
            "maxDrawdown": 0,
            "profitFactor": 0,
            "avgHoldTime": "-"
        }
        for s in STRATEGIES
    ]
