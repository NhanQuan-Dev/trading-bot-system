"""
Risk Monitoring Service - Giám sát rủi ro real-time cho giao dịch.

Mục đích:
- Monitor exposure, position size, daily loss, margin.
- Quản lý risk limits và alerts khẩn cấp.

Liên quan đến file nào:
- Sử dụng models từ trading/infrastructure/persistence/models/core_models.py (RiskLimitModel, etc.).
- Sử dụng enums từ trading/domain/ (BotStatus, PositionSide).
- Khi gặp bug: Kiểm tra calculations với Decimal, verify DB queries, hoặc log trong shared/exceptions/.
"""

"""
Risk Management Service for trading platform.

Provides real-time risk monitoring, exposure analysis, risk limits management,
and emergency controls for trading portfolios.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.orm import selectinload

from trading.infrastructure.persistence.models.core_models import (
    BotModel, PositionModel, UserModel, RiskLimitModel, RiskAlertModel
)
from trading.domain.bot.enums import BotStatus
from trading.domain.portfolio.enums import PositionSide


class RiskStatus(str, Enum):
    """Risk status levels - Các mức rủi ro."""
    SAFE = "safe"  # An toàn
    WARNING = "warning"  # Cảnh báo
    DANGER = "danger"  # Nguy hiểm


class AlertSeverity(str, Enum):
    """Risk alert severity levels - Mức độ nghiêm trọng của alert."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of risk alerts - Các loại alert rủi ro."""
    POSITION_SIZE = "position_size"  # Kích thước vị thế
    DAILY_LOSS = "daily_loss"  # Thua lỗ hàng ngày
    EXPOSURE = "exposure"  # Tiếp xúc rủi ro
    MARGIN = "margin"  # Margin
    DRAWDOWN = "drawdown"  # Drawdown


@dataclass
class RiskOverview:
    """Risk dashboard overview data - Tổng quan dashboard rủi ro."""
    current_exposure: float  # Tiếp xúc hiện tại
    leverage_used: float
    margin_level: float
    risk_score: int  # 1-100
    active_alerts: int


@dataclass
class ExposureBreakdown:
    """Asset exposure breakdown."""
    asset: str
    exposure_value: float
    exposure_pct: float
    limit: float
    status: RiskStatus


@dataclass
class RiskLimit:
    """Risk limit configuration."""
    type: str
    value: float
    current: float
    status: RiskStatus
    last_updated: datetime


@dataclass
class RiskAlert:
    """Risk alert data."""
    id: int
    type: AlertType
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime]
    is_active: bool


class RiskMonitoringService:
    """Service for risk monitoring and management."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the risk monitoring service."""
        self.db = db_session
    
    async def get_risk_overview(self, user_id: int) -> RiskOverview:
        """
        Get comprehensive risk overview for user's portfolio.
        
        Args:
            user_id: User ID to analyze
            
        Returns:
            RiskOverview with current risk status
        """
        # Get all active positions
        positions = await self._get_user_positions(user_id)
        
        # Calculate current exposure
        current_exposure = self._calculate_total_exposure(positions)
        
        # Calculate leverage usage
        leverage_used = await self._calculate_leverage_used(user_id)
        
        # Calculate margin level
        margin_level = await self._calculate_margin_level(user_id)
        
        # Calculate risk score
        risk_score = await self._calculate_risk_score(user_id, current_exposure, leverage_used, margin_level)
        
        # Count active alerts
        active_alerts = await self._count_active_alerts(user_id)
        
        return RiskOverview(
            current_exposure=round(current_exposure, 2),
            leverage_used=round(leverage_used, 2),
            margin_level=round(margin_level, 2),
            risk_score=risk_score,
            active_alerts=active_alerts
        )
    
    async def get_exposure_breakdown(self, user_id: int) -> List[ExposureBreakdown]:
        """
        Get detailed exposure breakdown by asset.
        
        Args:
            user_id: User ID to analyze
            
        Returns:
            List of ExposureBreakdown objects
        """
        positions = await self._get_user_positions(user_id)
        
        # Group positions by asset
        asset_exposure = {}
        for position in positions:
            asset = position.symbol.split('/')[0]  # Extract base asset from symbol like BTC/USDT
            
            if asset not in asset_exposure:
                asset_exposure[asset] = []
            asset_exposure[asset].append(position)
        
        # Calculate exposure for each asset
        exposure_breakdown = []
        total_portfolio_value = await self._get_portfolio_value(user_id)
        
        for asset, asset_positions in asset_exposure.items():
            exposure_value = sum(
                float(pos.size) * float(pos.current_price or pos.entry_price)
                for pos in asset_positions
            )
            
            exposure_pct = (exposure_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            # Get asset exposure limit (default 25%)
            exposure_limit = await self._get_asset_exposure_limit(user_id, asset)
            
            # Determine risk status
            status = self._determine_exposure_status(exposure_pct, exposure_limit)
            
            exposure_breakdown.append(ExposureBreakdown(
                asset=asset,
                exposure_value=round(exposure_value, 2),
                exposure_pct=round(exposure_pct, 2),
                limit=exposure_limit,
                status=status
            ))
        
        return sorted(exposure_breakdown, key=lambda x: x.exposure_value, reverse=True)
    
    async def get_risk_limits(self, user_id: int) -> List[RiskLimit]:
        """
        Get user's risk limits configuration.
        
        Args:
            user_id: User ID to get limits for
            
        Returns:
            List of RiskLimit objects
        """
        stmt = (
            select(RiskLimitModel)
            .where(RiskLimitModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        risk_limits_db = result.scalars().all()
        
        risk_limits = []
        for limit in risk_limits_db:
            # Calculate current value for each limit type
            current_value = await self._calculate_current_limit_value(user_id, limit.limit_type)
            
            # Determine status
            if limit.max_value and current_value > limit.max_value:
                status = RiskStatus.DANGER
            elif limit.max_value and current_value > limit.max_value * 0.8:
                status = RiskStatus.WARNING
            else:
                status = RiskStatus.SAFE
            
            risk_limits.append(RiskLimit(
                type=limit.limit_type,
                value=float(limit.max_value or 0),
                current=round(current_value, 2),
                status=status,
                last_updated=limit.updated_at
            ))
        
        return risk_limits
    
    async def update_risk_limits(
        self, 
        user_id: int, 
        position_size_limit: Optional[float] = None,
        daily_loss_limit: Optional[float] = None,
        exposure_limit: Optional[float] = None
    ) -> List[RiskLimit]:
        """
        Update user's risk limits.
        
        Args:
            user_id: User ID to update limits for
            position_size_limit: Maximum position size limit
            daily_loss_limit: Maximum daily loss limit
            exposure_limit: Maximum portfolio exposure limit
            
        Returns:
            Updated list of RiskLimit objects
        """
        limits_to_update = []
        
        if position_size_limit is not None:
            limits_to_update.append(("position_size", position_size_limit))
        if daily_loss_limit is not None:
            limits_to_update.append(("daily_loss", daily_loss_limit))
        if exposure_limit is not None:
            limits_to_update.append(("exposure", exposure_limit))
        
        for limit_type, limit_value in limits_to_update:
            # Check if limit exists
            stmt = select(RiskLimitModel).where(
                and_(
                    RiskLimitModel.user_id == user_id,
                    RiskLimitModel.limit_type == limit_type
                )
            )
            result = await self.db.execute(stmt)
            existing_limit = result.scalars().first()
            
            if existing_limit:
                # Update existing limit
                stmt = (
                    update(RiskLimitModel)
                    .where(RiskLimitModel.id == existing_limit.id)
                    .values(max_value=Decimal(str(limit_value)), updated_at=datetime.utcnow())
                )
                await self.db.execute(stmt)
            else:
                # Create new limit
                new_limit = RiskLimitModel(
                    user_id=user_id,
                    limit_type=limit_type,
                    max_value=Decimal(str(limit_value)),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(new_limit)
        
        await self.db.commit()
        return await self.get_risk_limits(user_id)
    
    async def get_risk_alerts(
        self, 
        user_id: int, 
        limit: int = 50,
        offset: int = 0
    ) -> List[RiskAlert]:
        """
        Get risk alerts history for user.
        
        Args:
            user_id: User ID to get alerts for
            limit: Maximum number of alerts to return
            offset: Number of alerts to skip
            
        Returns:
            List of RiskAlert objects
        """
        stmt = (
            select(RiskAlertModel)
            .where(RiskAlertModel.user_id == user_id)
            .order_by(desc(RiskAlertModel.triggered_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        alerts_db = result.scalars().all()
        
        alerts = []
        for alert in alerts_db:
            alerts.append(RiskAlert(
                id=alert.id,
                type=AlertType(alert.alert_type),
                severity=AlertSeverity(alert.severity),
                message=alert.message,
                triggered_at=alert.triggered_at,
                resolved_at=alert.resolved_at,
                is_active=alert.resolved_at is None
            ))
        
        return alerts
    
    async def emergency_stop_all_bots(
        self, 
        user_id: int, 
        reason: str
    ) -> Dict[str, Any]:
        """
        Emergency stop all user's active bots and close positions.
        
        Args:
            user_id: User ID to stop all bots for
            reason: Reason for emergency stop
            
        Returns:
            Summary of stopped bots and closed positions
        """
        # Get all active bots
        stmt = (
            select(BotModel)
            .where(
                and_(
                    BotModel.user_id == user_id,
                    BotModel.status == BotStatus.RUNNING
                )
            )
            .options(selectinload(BotModel.positions))
        )
        result = await self.db.execute(stmt)
        active_bots = result.scalars().all()
        
        stopped_bots = []
        closed_positions = []
        
        for bot in active_bots:
            # Stop the bot
            stmt = (
                update(BotModel)
                .where(BotModel.id == bot.id)
                .values(
                    status=BotStatus.STOPPED,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(stmt)
            stopped_bots.append(bot.id)
            
            # Close all open positions for this bot
            for position in bot.positions:
                if position.size and position.size != 0:
                    # Mark position as closed (simplified - in real implementation would place market orders)
                    stmt = (
                        update(PositionModel)
                        .where(PositionModel.id == position.id)
                        .values(
                            size=Decimal('0'),
                            updated_at=datetime.utcnow()
                        )
                    )
                    await self.db.execute(stmt)
                    closed_positions.append(position.id)
        
        # Create emergency alert
        emergency_alert = RiskAlertModel(
            user_id=user_id,
            alert_type=AlertType.MARGIN.value,
            severity=AlertSeverity.CRITICAL.value,
            message=f"EMERGENCY STOP: {reason}. All bots stopped and positions closed.",
            triggered_at=datetime.utcnow()
        )
        self.db.add(emergency_alert)
        
        await self.db.commit()
        
        return {
            "stopped_bots": len(stopped_bots),
            "closed_positions": len(closed_positions),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Private helper methods
    
    async def _get_user_positions(self, user_id: int) -> List[PositionModel]:
        """Get all active positions for user."""
        stmt = (
            select(PositionModel)
            .join(BotModel, PositionModel.bot_id == BotModel.id)
            .where(
                and_(
                    BotModel.user_id == user_id,
                    PositionModel.size != 0
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    def _calculate_total_exposure(self, positions: List[PositionModel]) -> float:
        """Calculate total exposure value from positions."""
        total_exposure = 0.0
        for position in positions:
            position_value = float(position.size or 0) * float(position.current_price or position.entry_price)
            total_exposure += abs(position_value)
        return total_exposure
    
    async def _calculate_leverage_used(self, user_id: int) -> float:
        """Calculate current leverage usage."""
        positions = await self._get_user_positions(user_id)
        total_exposure = self._calculate_total_exposure(positions)
        portfolio_value = await self._get_portfolio_value(user_id)
        
        if portfolio_value == 0:
            return 0.0
        
        return total_exposure / portfolio_value
    
    async def _calculate_margin_level(self, user_id: int) -> float:
        """Calculate margin level (equity / margin used)."""
        # Simplified calculation - in real implementation would calculate from exchange margin data
        return 150.0  # Placeholder - would need real margin calculations
    
    async def _calculate_risk_score(
        self, 
        user_id: int, 
        exposure: float, 
        leverage: float, 
        margin_level: float
    ) -> int:
        """
        Calculate risk score (1-100).
        
        Risk score algorithm:
        1-30: Low risk (green)
        31-60: Medium risk (yellow)  
        61-100: High risk (red)
        """
        # Get recent drawdown
        drawdown = await self._get_recent_drawdown(user_id)
        
        # Weighted risk calculation
        exposure_score = min(exposure / 100000 * 30, 30)  # 30% weight for exposure
        leverage_score = min(leverage * 15, 25)  # 25% weight for leverage
        margin_score = max(25 - (margin_level - 100) / 10, 0)  # 25% weight for margin
        drawdown_score = min(drawdown * 2, 20)  # 20% weight for drawdown
        
        risk_score = int(exposure_score + leverage_score + margin_score + drawdown_score)
        return min(max(risk_score, 1), 100)
    
    async def _count_active_alerts(self, user_id: int) -> int:
        """Count active risk alerts for user."""
        stmt = (
            select(func.count(RiskAlertModel.id))
            .where(
                and_(
                    RiskAlertModel.user_id == user_id,
                    RiskAlertModel.resolved_at.is_(None)
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_portfolio_value(self, user_id: int) -> float:
        """Get total portfolio value for user."""
        # Simplified - would calculate from actual balance + positions value
        return 10000.0  # Placeholder
    
    async def _get_asset_exposure_limit(self, user_id: int, asset: str) -> float:
        """Get exposure limit for specific asset."""
        # Check if user has custom limit for this asset
        stmt = (
            select(RiskLimitModel)
            .where(
                and_(
                    RiskLimitModel.user_id == user_id,
                    RiskLimitModel.limit_type == f"exposure_{asset.lower()}"
                )
            )
        )
        result = await self.db.execute(stmt)
        limit = result.scalars().first()
        
        if limit and limit.max_value:
            return float(limit.max_value)
        
        # Default asset exposure limit
        return 25.0  # 25% default
    
    def _determine_exposure_status(self, current_pct: float, limit_pct: float) -> RiskStatus:
        """Determine risk status based on exposure percentage."""
        if current_pct >= limit_pct:
            return RiskStatus.DANGER
        elif current_pct >= limit_pct * 0.8:
            return RiskStatus.WARNING
        else:
            return RiskStatus.SAFE
    
    async def _calculate_current_limit_value(self, user_id: int, limit_type: str) -> float:
        """Calculate current value for a risk limit type."""
        if limit_type == "position_size":
            positions = await self._get_user_positions(user_id)
            if not positions:
                return 0.0
            return max(abs(float(pos.size or 0)) * float(pos.current_price or pos.entry_price) 
                      for pos in positions)
        
        elif limit_type == "daily_loss":
            # Calculate today's P&L (simplified)
            return 0.0  # Would calculate from today's trades
        
        elif limit_type == "exposure":
            positions = await self._get_user_positions(user_id)
            return self._calculate_total_exposure(positions)
        
        return 0.0
    
    async def _get_recent_drawdown(self, user_id: int) -> float:
        """Get recent drawdown percentage."""
        # Simplified - would calculate from equity curve
        return 5.0  # Placeholder 5% drawdown