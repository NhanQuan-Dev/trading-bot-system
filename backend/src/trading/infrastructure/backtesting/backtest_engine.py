"""Backtesting engine for strategy simulation."""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Callable
from datetime import datetime

from ...domain.backtesting import (
    BacktestRun,
    BacktestTrade,
    BacktestPosition,
    BacktestResults,
    BacktestConfig,
    BacktestMode,
    BacktestStatus,
    TradeDirection,
    EquityCurvePoint,
    PerformanceMetrics,
)
from .metrics_calculator import MetricsCalculator
from .market_simulator import MarketSimulator

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Event-driven backtesting engine."""
    
    def __init__(
        self,
        config: BacktestConfig,
        metrics_calculator: Optional[MetricsCalculator] = None,
        market_simulator: Optional[MarketSimulator] = None,
    ):
        """Initialize backtesting engine."""
        self.config = config
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        self.market_simulator = market_simulator or MarketSimulator(
            slippage_model=config.slippage_model,
            slippage_percent=config.slippage_percent,
            commission_model=config.commission_model,
            commission_rate=config.commission_percent,  # Note: MarketSimulator param is commission_rate
        )
        
        # State
        self.equity = config.initial_capital
        self.peak_equity = config.initial_capital
        self.current_position: Optional[BacktestPosition] = None
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[EquityCurvePoint] = []
        
        # Stats
        self.total_bars_processed = 0
        self.signals_generated = 0
    
    async def run_backtest(
        self,
        candles: List[Dict],
        strategy_func: Callable,
        backtest_run: BacktestRun,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> BacktestResults:
        """
        Run backtest simulation.
        
        Args:
            candles: List of OHLCV candle data
            strategy_func: Strategy function that generates signals
            backtest_run: BacktestRun entity for tracking
            progress_callback: Optional callback for progress updates
        
        Returns:
            BacktestResults with complete performance analysis
        """
        
        logger.info(f"Starting backtest with {len(candles)} candles")
        backtest_run.start()
        
        try:
            # Process each candle
            total_candles = len(candles)
            
            for idx, candle in enumerate(candles):
                self.total_bars_processed += 1
                
                # Process candle
                self._process_candle(candle, strategy_func, idx)
                
                # Update progress
                if progress_callback and idx % 10 == 0:
                    percent = int((idx / total_candles) * 100)
                    backtest_run.update_progress(percent)
                    await progress_callback(percent)
                
                # Log every 50 candles
                # Log every 50 candles
                if idx % 50 == 0:
                    logger.debug(f"Progress: {idx}/{total_candles} candles | Signals: {self.signals_generated} | Trades: {len(self.trades)}")
            
            # Close any open position
            if self.current_position:
                final_candle = candles[-1]
                self._close_position(
                    price=Decimal(str(final_candle["close"])),
                    timestamp=final_candle["timestamp"],
                    reason="End of backtest",
                )
            
            # Calculate final metrics
            duration_days = self._calculate_duration_days(candles[0]["timestamp"], candles[-1]["timestamp"])
            
            metrics = self.metrics_calculator.calculate_performance_metrics(
                trades=self.trades,
                equity_curve=self.equity_curve,
                initial_capital=self.config.initial_capital,
                duration_days=duration_days,
            )
            
            # Create results
            results = BacktestResults(
                start_date=candles[0]["timestamp"] if isinstance(candles[0]["timestamp"], datetime) else datetime.fromisoformat(candles[0]["timestamp"]),
                end_date=candles[-1]["timestamp"] if isinstance(candles[-1]["timestamp"], datetime) else datetime.fromisoformat(candles[-1]["timestamp"]),
                duration_days=duration_days,
                initial_capital=self.config.initial_capital,
                final_equity=self.equity,
                peak_equity=self.peak_equity,
                metrics=metrics,  # Changed from performance_metrics
                equity_curve=self.equity_curve,
                trades=self.trades,
            )
            
            backtest_run.complete(results)
            
            logger.info(f"Backtest completed: {len(self.trades)} trades, {metrics.total_return}% return")
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            backtest_run.fail(str(e))
            raise
    
    def _process_candle(
        self,
        candle: Dict,
        strategy_func: Callable,
        candle_idx: int,
    ) -> None:
        """Process single candle through strategy logic."""
        
        # Update current position metrics
        current_price = Decimal(str(candle["close"]))
        
        if self.current_position:
            self.current_position.update_unrealized_pnl(current_price)
            
            # Check stop loss / take profit
            if self._should_close_position(current_price):
                self._close_position(
                    price=current_price,
                    timestamp=candle["timestamp"],
                    reason="Stop loss / Take profit",
                )
                return
        
        # Generate strategy signal
        signal = strategy_func(candle, candle_idx, self.current_position)
        
        if signal:
            self.signals_generated += 1
            logger.debug(f"Signal #{self.signals_generated} at idx={candle_idx}: {signal['type']}")
            self._process_signal(signal, candle)
        
        # Update equity curve
        self._update_equity_curve(candle["timestamp"], current_price)
    
    def _process_signal(self, signal: Dict, candle: Dict) -> None:
        """Process trading signal from strategy."""
        
        signal_type = signal.get("type")  # "buy", "sell", "close"
        current_price = Decimal(str(candle["close"]))
        
        if signal_type == "buy" and not self.current_position:
            self._open_long_position(
                price=current_price,
                timestamp=candle["timestamp"],
                signal=signal,
            )
        
        elif signal_type == "sell" and not self.current_position:
            self._open_short_position(
                price=current_price,
                timestamp=candle["timestamp"],
                signal=signal,
            )
        
        elif signal_type == "close" and self.current_position:
            self._close_position(
                price=current_price,
                timestamp=candle["timestamp"],
                reason="Signal close",
            )
    
    def _open_long_position(
        self,
        price: Decimal,
        timestamp: str,
        signal: Dict,
    ) -> None:
        """Open long position."""
        
        # Calculate position size
        quantity = self._calculate_position_size(price)
        
        # Simulate order execution
        fill = self.market_simulator.simulate_buy_order(
            symbol=self.config.symbol,
            quantity=quantity,
            current_price=price,
            timestamp=timestamp,
        )
        
        if fill.filled_quantity == 0:
            return  # Order not filled
        
        # Create position
        self.current_position = BacktestPosition(
            symbol=self.config.symbol,
            direction=TradeDirection.LONG,
            quantity=fill.filled_quantity,
            avg_entry_price=fill.filled_price,
        )
        # Store stop loss/take profit separately if needed
        self.current_position.stop_loss = signal.get("stop_loss")
        self.current_position.take_profit = signal.get("take_profit")
        self.current_position.entry_time = timestamp
        
        # Deduct cost from equity
        cost = fill.filled_price * fill.filled_quantity + fill.commission
        self.equity -= cost
        
        logger.debug(f"Opened LONG: {fill.filled_quantity} @ {fill.filled_price}")
    
    def _open_short_position(
        self,
        price: Decimal,
        timestamp: str,
        signal: Dict,
    ) -> None:
        """Open short position."""
        
        # Calculate position size
        quantity = self._calculate_position_size(price)
        
        # Simulate order execution
        fill = self.market_simulator.simulate_sell_order(
            symbol=self.config.symbol,
            quantity=quantity,
            current_price=price,
            timestamp=timestamp,
        )
        
        if fill.filled_quantity == 0:
            return
        
        # Create position
        self.current_position = BacktestPosition(
            symbol=self.config.symbol,
            direction=TradeDirection.SHORT,
            quantity=fill.filled_quantity,
            avg_entry_price=fill.filled_price,
        )
        # Store stop loss/take profit separately if needed
        self.current_position.stop_loss = signal.get("stop_loss")
        self.current_position.take_profit = signal.get("take_profit")
        self.current_position.entry_time = timestamp
        
        # Add proceeds to equity
        proceeds = fill.filled_price * fill.filled_quantity - fill.commission
        self.equity += proceeds
        
        logger.debug(f"Opened SHORT: {fill.filled_quantity} @ {fill.filled_price}")
    
    def _close_position(
        self,
        price: Decimal,
        timestamp: str,
        reason: str,
    ) -> None:
        """Close current position and record trade."""
        
        if not self.current_position:
            return
        
        # Simulate order execution
        if self.current_position.direction == TradeDirection.LONG:
            fill = self.market_simulator.simulate_sell_order(
                symbol=self.config.symbol,
                quantity=self.current_position.quantity,
                current_price=price,
                timestamp=timestamp,
            )
        else:
            fill = self.market_simulator.simulate_buy_order(
                symbol=self.config.symbol,
                quantity=self.current_position.quantity,
                current_price=price,
                timestamp=timestamp,
            )
        
        if fill.filled_quantity == 0:
            return
        
        # Calculate P&L
        if self.current_position.direction == TradeDirection.LONG:
            pnl = (fill.filled_price - self.current_position.avg_entry_price) * fill.filled_quantity
            self.equity += fill.filled_price * fill.filled_quantity - fill.commission
        else:
            pnl = (self.current_position.avg_entry_price - fill.filled_price) * fill.filled_quantity
            self.equity -= fill.filled_price * fill.filled_quantity + fill.commission
        
        # Calculate net P&L and percentage
        total_costs = fill.commission + fill.slippage
        net_pnl = pnl - total_costs
        
        entry_value = self.current_position.avg_entry_price * fill.filled_quantity
        pnl_percent = (net_pnl / entry_value) * Decimal("100") if entry_value > 0 else Decimal("0")
        
        # Create trade record
        trade = BacktestTrade(
            symbol=self.config.symbol,
            direction=self.current_position.direction,
            entry_price=self.current_position.avg_entry_price,
            exit_price=fill.filled_price,
            entry_quantity=fill.filled_quantity,  # Changed from 'quantity'
            entry_time=self.current_position.entry_time if hasattr(self.current_position, 'entry_time') else datetime.utcnow(),
            exit_time=timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            gross_pnl=pnl,
            net_pnl=net_pnl,
            pnl_percent=pnl_percent,
            entry_commission=Decimal("0"),  # Not tracked separately
            exit_commission=fill.commission,
            entry_slippage=Decimal("0"),  # Not tracked separately  
            exit_slippage=fill.slippage,
        )
        # Trade is complete - no need to call close()
        
        self.trades.append(trade)
        self.current_position = None
        
        # Update peak equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        logger.debug(f"Closed position: P&L={pnl}, equity={self.equity}")
    
    def _should_close_position(self, current_price: Decimal) -> bool:
        """Check if position should be closed due to stop/target."""
        
        if not self.current_position:
            return False
        
        # Check stop loss
        if self.current_position.stop_loss:
            if self.current_position.direction == TradeDirection.LONG:
                if current_price <= self.current_position.stop_loss:
                    return True
            else:
                if current_price >= self.current_position.stop_loss:
                    return True
        
        # Check take profit
        if self.current_position.take_profit:
            if self.current_position.direction == TradeDirection.LONG:
                if current_price >= self.current_position.take_profit:
                    return True
            else:
                if current_price <= self.current_position.take_profit:
                    return True
        
        return False
    
    def _calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate position size based on sizing method."""
        
        # Use config position sizing
        if self.config.position_size_value:
            capital_to_use = self.equity * self.config.position_size_value  # Already in decimal form (0.1 = 10%)
            quantity = capital_to_use / price
            return quantity
        
        # Default: use full capital
        return self.equity / price
    
    def _update_equity_curve(self, timestamp: str, current_price: Decimal) -> None:
        """Update equity curve with current state."""
        
        # Calculate current total equity including unrealized P&L
        total_equity = self.equity
        if self.current_position:
            total_equity += self.current_position.unrealized_pnl or Decimal("0")
        
        # Calculate drawdown
        drawdown_amount = total_equity - self.peak_equity
        drawdown_percent = (drawdown_amount / self.peak_equity * Decimal("100")) if self.peak_equity > 0 else Decimal("0")
        
        # Calculate return
        return_percent = ((total_equity - self.config.initial_capital) / self.config.initial_capital * Decimal("100"))
        
        # Calculate positions value
        positions_value = Decimal("0")
        if self.current_position:
            positions_value = self.current_position.quantity * current_price
        
        point = EquityCurvePoint(
            timestamp=timestamp,
            equity=total_equity,
            cash=self.equity,  # Current cash balance
            positions_value=positions_value,  # Value of open positions
            drawdown=drawdown_amount,  # Drawdown amount
            drawdown_percent=drawdown_percent,
            return_percent=return_percent,
        )
        
        self.equity_curve.append(point)
    
    def _calculate_duration_days(self, start_time: str, end_time: str) -> int:
        """Calculate backtest duration in days."""
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            duration = (end_dt - start_dt).days
            return max(duration, 1)
        except:
            return 1
