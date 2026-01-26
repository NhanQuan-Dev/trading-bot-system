from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Any
from ....infrastructure.persistence.database import get_db
from ....infrastructure.persistence.models.bot_models import StrategyModel

router = APIRouter()

@router.get("", response_model=List[Any])
async def get_strategies(db: AsyncSession = Depends(get_db)):
    """
    Get a list of all available trading strategies from the database.
    """
    stmt = select(StrategyModel)
    result = await db.execute(stmt)
    strategies = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "type": s.strategy_type,
            "description": s.description,
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
        for s in strategies
    ]
