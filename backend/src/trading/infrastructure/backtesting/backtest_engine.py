"""Backtesting engine for strategy simulation."""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Callable, Union, Any
from datetime import datetime
from uuid import UUID

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
    BacktestEventType,
    BacktestEvent,
)
from .metrics_calculator import MetricsCalculator
from .market_simulator import MarketSimulator
from .timeframe_utils import resample_candles_to_htf, get_candles_in_htf_window

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
            fill_policy=config.fill_policy,  # Spec-required: Pass fill policy configuration
        )
        
        # State
        self.equity = config.initial_capital
        self.peak_equity = config.initial_capital
        self.current_position: Optional[BacktestPosition] = None
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[EquityCurvePoint] = []
        
        # Spec-required: Current trade tracking
        self.current_trade_signal_time: Optional[datetime] = None
        self.current_trade_max_drawdown: Decimal = Decimal("0")
        self.current_trade_max_runup: Decimal = Decimal("0")
        self.current_trade_fill_policy: Optional[str] = None
        self.current_trade_fill_conditions: Optional[dict] = None
        
        # Spec-required Phase 2: Event tracking
        self.events: List[BacktestEvent] = []
        self.backtest_run_id: Optional[UUID] = None  # Set when backtest starts
        
        # Stats
        self.equity_curve: List[EquityCurvePoint] = []
        self.last_funding_time: Optional[datetime] = None
        
        # Stats
        self.total_bars_processed = 0
        self.signals_generated = 0
    
    def _emit_event(
        self,
        event_type: BacktestEventType,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Emit a backtest event for debugging and replay."""
        if not self.backtest_run_id:
            # Events only recorded when backtest run is active
            return
        
        event = BacktestEvent(
            backtest_id=self.backtest_run_id,
            event_type=event_type,
            timestamp=timestamp or datetime.utcnow(),
            details=details,
        )
        self.events.append(event)
    
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
        
        # Set backtest run ID for event tracking
        self.backtest_run_id = backtest_run.id
        
        logger.info(f"Starting backtest with {len(candles)} candles")
        
        # Only start if still pending (might already be RUNNING if use case started it during data fetch)
        # Handle both enum (BacktestStatus.PENDING) and string ('pending') comparisons
        current_status = backtest_run.status
        is_pending = (
            current_status == BacktestStatus.PENDING or 
            (isinstance(current_status, str) and current_status.lower() == 'pending')
        )
        
        if is_pending:
            backtest_run.start()
        
        try:
            # Spec-required: Multi-timeframe processing
            if self.config.signal_timeframe != "1m":
                # HTF Signal Mode: Resample 1m → HTF, replay 1m for execution
                logger.info(f"Multi-timeframe mode: data={self.config.data_timeframe}, signal={self.config.signal_timeframe}")
                
                htf_candles = resample_candles_to_htf(candles, self.config.signal_timeframe)
                total_htf = len(htf_candles)
                
                for htf_idx, htf_candle in enumerate(htf_candles):
                    # Emit HTF candle closed event
                    self._emit_event(
                        BacktestEventType.HTF_CANDLE_CLOSED,
                        {
                            "timeframe": self.config.signal_timeframe,
                            "open": htf_candle["open"],
                            "high": htf_candle["high"],
                            "low": htf_candle["low"],
                            "close": htf_candle["close"],
                        },
                        datetime.fromisoformat(htf_candle["timestamp"]) if isinstance(htf_candle["timestamp"], str) else htf_candle["timestamp"],
                    )
                    
                    # Generate HTF signal
                    htf_signal = strategy_func(htf_candle, htf_idx, self.current_position)
                    
                    if htf_signal:
                        self.signals_generated += 1
                        logger.debug(f"HTF Signal #{self.signals_generated} at HTF idx={htf_idx}: {htf_signal['type']}")
                    
                    # Get 1m candles within this HTF window for execution
                    htf_timestamp = datetime.fromisoformat(htf_candle["timestamp"]) if isinstance(htf_candle["timestamp"], str) else htf_candle["timestamp"]
                    window_1m_candles = get_candles_in_htf_window(candles, htf_timestamp, self.config.signal_timeframe)
                    
                    # Replay 1m candles for precision execution and TP/SL checks
                    for m1_candle in window_1m_candles:
                        self.total_bars_processed += 1
                        
                        # Process HTF signal on first 1m candle of window
                        if htf_signal and m1_candle == window_1m_candles[0]:
                            self._process_signal(htf_signal, m1_candle)
                        
                        # Always check SL/TP and update metrics on every 1m candle
                        if self.current_position:
                            current_price = Decimal(str(m1_candle["close"]))
                            self.current_position.update_unrealized_pnl(current_price)
                            
                            # Track max_drawdown/runup
                            if self.current_position.unrealized_pnl < self.current_trade_max_drawdown:
                                self.current_trade_max_drawdown = self.current_position.unrealized_pnl
                            if self.current_position.unrealized_pnl > self.current_trade_max_runup:
                                self.current_trade_max_runup = self.current_position.unrealized_pnl
                            
                            # Check SL/TP
                            candle_high = Decimal(str(m1_candle.get("high", m1_candle["close"])))
                            candle_low = Decimal(str(m1_candle.get("low", m1_candle["close"])))
                            candle_open = Decimal(str(m1_candle.get("open", m1_candle["close"])))
                            
                            sl_tp_result = self._check_sl_tp_trailing_with_high_low(candle_high, candle_low, candle_open)
                            if sl_tp_result:
                                close_price, reason = sl_tp_result
                                self._close_position(
                                    price=close_price,
                                    timestamp=m1_candle["timestamp"],
                                    reason=reason,
                                )
                        
                        # Update equity curve
                        self._update_equity_curve(m1_candle["timestamp"], Decimal(str(m1_candle["close"])))
                    
                    # Progress update per HTF candle
                    if progress_callback and htf_idx % max(1, int(total_htf / 20)) == 0:
                        percent = int((htf_idx / total_htf) * 100)
                        backtest_run.update_progress(percent)
                        await progress_callback(percent)
                
            else:
                # Standard 1m processing (original logic)
                total_candles = len(candles)
                
                for idx, candle in enumerate(candles):
                    self.total_bars_processed += 1
                    
                    # Process candle
                    self._process_candle(candle, strategy_func, idx)
                    
                    # Update progress
                    update_step = max(100, int(total_candles / 100))
                    
                    if progress_callback and idx % update_step == 0:
                        percent = int((idx / total_candles) * 100)
                        backtest_run.update_progress(percent)
                        await progress_callback(percent)
                    
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
        
        # Check Funding Fee
        self._check_funding(candle)
        
        if self.current_position:
            self.current_position.update_unrealized_pnl(current_price)
            
            # Spec-required: Track intra-trade max drawdown and runup
            if self.current_position.unrealized_pnl < self.current_trade_max_drawdown:
                self.current_trade_max_drawdown = self.current_position.unrealized_pnl
            if self.current_position.unrealized_pnl > self.current_trade_max_runup:
                self.current_trade_max_runup = self.current_position.unrealized_pnl
            
            # Level 2 SL/TP Check: Use High/Low prices for more accurate simulation
            candle_high = Decimal(str(candle.get("high", candle["close"])))
            candle_low = Decimal(str(candle.get("low", candle["close"])))
            
            # Update trailing stop (must happen BEFORE checking if triggered)
            self.current_position.update_trailing_stop(candle_high, candle_low)
            
            # Check SL/TP/Trailing with High/Low
            # Priority 0: Liquidation Check (Before SL/TP)
            liquidation_result = self._check_liquidation(candle_high, candle_low)
            if liquidation_result:
                close_price, reason = liquidation_result
                logger.warning(f"LIQUIDATION Triggered at {close_price} ({reason})")
                self._close_position(
                    price=close_price,
                    timestamp=candle["timestamp"],
                    reason=reason,
                )
                return

            # Spec-required: Pass candle_open for realistic price path assumption
            candle_open = Decimal(str(candle.get("open", candle["close"])))
            sl_tp_result = self._check_sl_tp_trailing_with_high_low(candle_high, candle_low, candle_open)
            
            if sl_tp_result:
                close_price, reason = sl_tp_result
                self._close_position(
                    price=close_price,
                    timestamp=candle["timestamp"],
                    reason=reason,
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
        """Process trading signal from strategy.
        
        Supported signal types:
        - open_long: Open new LONG position (from flat)
        - open_short: Open new SHORT position (from flat)
        - add_long: Add to existing LONG (scale in)
        - add_short: Add to existing SHORT (scale in)
        - close_position: Close entire position
        - partial_close: Close specified quantity
        - reduce_long: Reduce LONG by quantity
        - reduce_short: Reduce SHORT by quantity
        - flip_long: Close SHORT and open LONG
        - flip_short: Close LONG and open SHORT
        """
        signal_type = signal.get("type")
        signal_quantity = signal.get("quantity")  # Optional quantity override
        current_price = Decimal(str(candle["close"]))
        timestamp = candle["timestamp"]
        
        # === OPEN NEW POSITIONS (from flat) ===
        if signal_type in ("open_long", "buy") and not self.current_position:
            self._open_long_position(price=current_price, timestamp=timestamp, signal=signal)
        
        elif signal_type in ("open_short", "sell") and not self.current_position:
            self._open_short_position(price=current_price, timestamp=timestamp, signal=signal)
        
        # === ADD TO EXISTING POSITIONS (scale in) ===
        elif signal_type == "add_long" and self._is_long():
            self._add_to_position(price=current_price, timestamp=timestamp, quantity=signal_quantity)
        
        elif signal_type == "add_short" and self._is_short():
            self._add_to_position(price=current_price, timestamp=timestamp, quantity=signal_quantity)
        
        # === CLOSE ENTIRE POSITION ===
        elif signal_type in ("close_position", "close") and self.current_position:
            reason = signal.get("metadata") or "Signal close"
            self._close_position(price=current_price, timestamp=timestamp, reason=reason)
        
        # === PARTIAL CLOSE / REDUCE ===
        elif signal_type == "partial_close" and self.current_position:
            reason = signal.get("metadata") or "Partial Close"
            self._partial_close(price=current_price, timestamp=timestamp, quantity=signal_quantity, reason=reason)
        
        elif signal_type == "reduce_long" and self._is_long():
            reason = signal.get("metadata") or "Reduce Long"
            self._partial_close(price=current_price, timestamp=timestamp, quantity=signal_quantity, reason=reason)
        
        elif signal_type == "reduce_short" and self._is_short():
            reason = signal.get("metadata") or "Reduce Short"
            self._partial_close(price=current_price, timestamp=timestamp, quantity=signal_quantity, reason=reason)
        
        # === FLIP POSITIONS ===
        elif signal_type == "flip_long" and self._is_short():
            reason = signal.get("metadata") or "Flip to LONG"
            self._close_position(price=current_price, timestamp=timestamp, reason=reason)
            self._open_long_position(price=current_price, timestamp=timestamp, signal=signal)
        
        elif signal_type == "flip_short" and self._is_long():
            self._close_position(price=current_price, timestamp=timestamp, reason="Flip to SHORT")
            self._open_short_position(price=current_price, timestamp=timestamp, signal=signal)
    
    def _is_long(self) -> bool:
        """Check if current position is LONG."""
        return self.current_position is not None and self.current_position.direction == TradeDirection.LONG
    
    def _is_short(self) -> bool:
        """Check if current position is SHORT."""
        return self.current_position is not None and self.current_position.direction == TradeDirection.SHORT
    
    def _open_long_position(
        self,
        price: Decimal,
        timestamp: str,
        signal: Dict,
    ) -> None:
        """Open long position."""
        
        # Calculate position size
        quantity = self._calculate_position_size(price)
        
        # Simulate LONG entry
        print(f"DEBUG: Processing Signal in _open_long_position: {signal}")
        fill = self.market_simulator.simulate_long_entry(
            symbol=self.config.symbol,
            quantity=quantity,
            current_price=price,
            timestamp=timestamp,
        )
        
        # Override commission with Taker Fee
        trade_value = fill.filled_quantity * fill.filled_price
        fill.commission = trade_value * self.config.taker_fee_rate
        
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
        self.current_position.entry_commission = fill.commission
        self.current_position.metadata = signal.get("metadata", signal.get("reason"))
        
        # Spec-required: Initialize trade tracking
        self.current_trade_signal_time = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp)
        self.current_trade_max_drawdown = Decimal("0")
        self.current_trade_max_runup = Decimal("0")
        self.current_trade_fill_policy = self.config.fill_policy
        self.current_trade_fill_conditions = fill.fill_conditions_met
        
        # Note: Don't modify equity when opening position
        # Equity will be updated when position is closed with realized PnL
        
        # Emit event
        self._emit_event(
            BacktestEventType.TRADE_OPENED,
            {
                "direction": "LONG",
                "price": float(fill.filled_price),
                "quantity": float(fill.filled_quantity),
                "stop_loss": float(signal.get("stop_loss")) if signal.get("stop_loss") else None,
                "take_profit": float(signal.get("take_profit")) if signal.get("take_profit") else None,
                "commission": float(fill.commission),
                "fill_conditions": fill.fill_conditions_met,
            },
            timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
        )
        
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
        
        # Simulate SHORT entry
        fill = self.market_simulator.simulate_short_entry(
            symbol=self.config.symbol,
            quantity=quantity,
            current_price=price,
            timestamp=timestamp,
        )
        
        # Override commission with Taker Fee
        trade_value = fill.filled_quantity * fill.filled_price
        fill.commission = trade_value * self.config.taker_fee_rate
        
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
        self.current_position.entry_commission = fill.commission
        self.current_position.metadata = signal.get("metadata", signal.get("reason"))
        
        # Note: Don't modify equity when opening position
        # Equity will be updated when position is closed with realized PnL
        
        logger.debug(f"Opened SHORT: {fill.filled_quantity} @ {fill.filled_price}")
    
    def _close_position(
        self,
        price: Decimal,
        timestamp: str,
        reason: Union[str, Dict[str, Any]],
    ) -> None:
        """Close current position and record trade."""
        
        if not self.current_position:
            return
        
        # Simulate position exit
        if self.current_position.direction == TradeDirection.LONG:
            # Closing LONG = SHORT entry action
            fill = self.market_simulator.simulate_short_entry(
                symbol=self.config.symbol,
                quantity=self.current_position.quantity,
                current_price=price,
                timestamp=timestamp,
            )
        else:
            # Closing SHORT = LONG entry action
            fill = self.market_simulator.simulate_long_entry(
                symbol=self.config.symbol,
                quantity=self.current_position.quantity,
                current_price=price,
                timestamp=timestamp,
            )
            
        # Override commission based on Maker/Taker
        is_maker = False
        if isinstance(reason, dict):
            r_str = str(reason.get("reason", "")).lower()
        else:
            r_str = str(reason).lower()
            
        if "take profit" in r_str or "tp" in r_str:
            is_maker = True
            
        rate = self.config.maker_fee_rate if is_maker else self.config.taker_fee_rate
        
        trade_value = fill.filled_quantity * fill.filled_price
        fill.commission = trade_value * rate
        
        if fill.filled_quantity == 0:
            return
        
        # Calculate P&L (same formula for both LONG and SHORT)
        if self.current_position.direction == TradeDirection.LONG:
            # LONG: profit when exit > entry
            pnl = (fill.filled_price - self.current_position.avg_entry_price) * fill.filled_quantity
        else:
            # SHORT: profit when entry > exit 
            pnl = (self.current_position.avg_entry_price - fill.filled_price) * fill.filled_quantity
        
        # Calculate total costs (entry + exit commissions)
        entry_commission = getattr(self.current_position, 'entry_commission', Decimal("0"))
        total_costs = entry_commission + fill.commission + fill.slippage
        net_pnl = pnl - total_costs
        
        # Update equity with net P&L
        self.equity += net_pnl
        
        entry_value = self.current_position.avg_entry_price * fill.filled_quantity
        pnl_percent = (net_pnl / entry_value) * Decimal("100") if entry_value > 0 else Decimal("0")
        
        # Normalize exit reason to dict
        exit_reason_dict = reason if isinstance(reason, dict) else {"reason": reason}

        # Spec-required: Calculate execution delay
        entry_time_dt = self.current_position.entry_time if isinstance(self.current_position.entry_time, datetime) else datetime.fromisoformat(self.current_position.entry_time)
        execution_delay_seconds = None
        if self.current_trade_signal_time:
            execution_delay_seconds = (entry_time_dt - self.current_trade_signal_time).total_seconds()

        # Create trade record
        trade = BacktestTrade(
            symbol=self.config.symbol,
            direction=self.current_position.direction,
            entry_price=self.current_position.avg_entry_price,
            exit_price=fill.filled_price,
            entry_quantity=fill.filled_quantity,
            entry_time=entry_time_dt,
            exit_time=timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            gross_pnl=pnl,
            net_pnl=net_pnl,
            pnl_percent=pnl_percent,
            entry_commission=Decimal("0"),
            exit_commission=fill.commission,
            entry_slippage=Decimal("0"), 
            exit_slippage=fill.slippage,
            entry_reason=getattr(self.current_position, 'metadata', None),
            exit_reason=exit_reason_dict,
            # Spec-required fields
            signal_time=self.current_trade_signal_time,
            execution_delay_seconds=execution_delay_seconds,
            max_drawdown=self.current_trade_max_drawdown,
            max_runup=self.current_trade_max_runup,
            fill_policy_used=self.current_trade_fill_policy,
            fill_conditions_met=self.current_trade_fill_conditions,
        print(f"DEBUG: Created BacktestTrade with exit_reason: {trade.exit_reason}")
        # Trade is complete - no need to call close()
        
        self.trades.append(trade)
        self.current_position = None
        
        # Emit TRADE_CLOSED event
        exit_event_type = BacktestEventType.TRADE_CLOSED
        r_str_lower = r_str  # Already lowered above
        if "stop loss" in r_str_lower or "sl" in r_str_lower:
            exit_event_type = BacktestEventType.SL_HIT
        elif "take profit" in r_str_lower or "tp" in r_str_lower:
            exit_event_type = BacktestEventType.TP_HIT
        elif "trailing" in r_str_lower:
            exit_event_type = BacktestEventType.TRAILING_STOP_HIT
        elif "liquidation" in r_str_lower:
            exit_event_type = BacktestEventType.LIQUIDATION
        
        self._emit_event(
            exit_event_type,
            {
                "direction": str(trade.direction),
                "exit_price": float(fill.filled_price),
                "pnl": float(net_pnl),
                "pnl_percent": float(pnl_percent),
                "exit_reason": exit_reason_dict,
                "max_drawdown": float(self.current_trade_max_drawdown),
                "max_runup": float(self.current_trade_max_runup),
            },
            timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
        )
        
        # Spec-required: Reset tracking variables
        self.current_trade_signal_time = None
        self.current_trade_max_drawdown = Decimal("0")
        self.current_trade_max_runup = Decimal("0")
        self.current_trade_fill_policy = None
        self.current_trade_fill_conditions = None
        
        # Update peak equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        logger.debug(f"Closed position: P&L={pnl}, equity={self.equity}")
    
    def _add_to_position(
        self,
        price: Decimal,
        timestamp: str,
        quantity: Optional[Decimal] = None,
    ) -> None:
        """Add to existing position (scale in / average in).
        
        Args:
            price: Current market price
            timestamp: Candle timestamp
            quantity: Amount to add (optional, uses default sizing if None)
        """
        if not self.current_position:
            return
        
        # Calculate quantity to add
        if quantity is not None:
            add_qty = Decimal(str(quantity))
        else:
            add_qty = self._calculate_position_size(price)
        
        # Simulate entry based on position direction
        if self.current_position.direction == TradeDirection.LONG:
            fill = self.market_simulator.simulate_long_entry(
                symbol=self.config.symbol,
                quantity=add_qty,
                current_price=price,
                timestamp=timestamp,
            )
        else:
            fill = self.market_simulator.simulate_short_entry(
                symbol=self.config.symbol,
                quantity=add_qty,
                current_price=price,
                timestamp=timestamp,
            )
        
        if fill.filled_quantity == 0:
            return
        
        # Calculate new average entry price (weighted average)
        old_value = self.current_position.avg_entry_price * self.current_position.quantity
        new_value = fill.filled_price * fill.filled_quantity
        total_qty = self.current_position.quantity + fill.filled_quantity
        new_avg_price = (old_value + new_value) / total_qty
        
        # Update position
        self.current_position.quantity = total_qty
        self.current_position.avg_entry_price = new_avg_price
        self.current_position.entry_commission += fill.commission
        
        logger.debug(
            f"Added to {self.current_position.direction.value}: "
            f"+{fill.filled_quantity} @ {fill.filled_price}, "
            f"total qty: {total_qty}, avg price: {new_avg_price}"
        )
    
    def _partial_close(
        self,
        price: Decimal,
        timestamp: str,
        quantity: Optional[Decimal] = None,
        reason: Union[str, Dict[str, Any]] = "Partial Close",
    ) -> None:
        """Close part of the current position.
        
        Args:
            price: Current market price
            timestamp: Candle timestamp
            quantity: Amount to close
            reason: Exit reason
        """
        if not self.current_position:
            return
        
        # Determine close quantity
        if quantity is not None:
            close_qty = min(Decimal(str(quantity)), self.current_position.quantity)
        else:
            # Default: close half the position
            close_qty = self.current_position.quantity / Decimal("2")
        
        if close_qty <= 0:
            return
        
        # Simulate exit for partial quantity
        if self.current_position.direction == TradeDirection.LONG:
            fill = self.market_simulator.simulate_short_entry(
                symbol=self.config.symbol,
                quantity=close_qty,
                current_price=price,
                timestamp=timestamp,
            )
        else:
            fill = self.market_simulator.simulate_long_entry(
                symbol=self.config.symbol,
                quantity=close_qty,
                current_price=price,
                timestamp=timestamp,
            )
        
        if fill.filled_quantity == 0:
            return
        
        # Calculate P&L for closed portion
        if self.current_position.direction == TradeDirection.LONG:
            pnl = (fill.filled_price - self.current_position.avg_entry_price) * fill.filled_quantity
        else:
            pnl = (self.current_position.avg_entry_price - fill.filled_price) * fill.filled_quantity
        
        # Calculate proportional entry commission
        proportion = fill.filled_quantity / (self.current_position.quantity + fill.filled_quantity)
        entry_commission = getattr(self.current_position, 'entry_commission', Decimal("0")) * proportion
        total_costs = entry_commission + fill.commission + fill.slippage
        net_pnl = pnl - total_costs
        
        # Update equity
        self.equity += net_pnl
        
        entry_value = self.current_position.avg_entry_price * fill.filled_quantity
        pnl_percent = (net_pnl / entry_value) * Decimal("100") if entry_value > 0 else Decimal("0")
        
        # Normalize exit reason
        exit_reason_dict = reason if isinstance(reason, dict) else {"reason": reason}

        # Record partial trade
        partial_trade = BacktestTrade(
            symbol=self.config.symbol,
            direction=self.current_position.direction,
            entry_price=self.current_position.avg_entry_price,
            exit_price=fill.filled_price,
            entry_quantity=fill.filled_quantity,
            entry_time=self.current_position.entry_time if hasattr(self.current_position, 'entry_time') else datetime.utcnow(),
            exit_time=timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            gross_pnl=pnl,
            net_pnl=net_pnl,
            pnl_percent=pnl_percent,
            entry_commission=entry_commission,
            exit_commission=fill.commission,
            entry_slippage=Decimal("0"),
            exit_slippage=fill.slippage,
            entry_reason=getattr(self.current_position, 'metadata', None),
            exit_reason=exit_reason_dict,
        )
        self.trades.append(partial_trade)
        
        # Update remaining position
        self.current_position.quantity -= fill.filled_quantity
        self.current_position.entry_commission -= entry_commission
        
        # Update peak equity
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        # If fully closed, clear position
        if self.current_position.quantity <= 0:
            self.current_position = None
        else:
            logger.debug(
                f"Partial close: {fill.filled_quantity} @ {fill.filled_price}, "
                f"remaining: {self.current_position.quantity}, P&L={pnl}"
            )
    
    
    def _check_funding(self, candle: Dict) -> None:
        """Apply funding fee if applicable."""
        if not self.config.collect_funding_fee or not self.current_position:
            return
            
        ts = candle["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
            
        # Funding times: 00:00, 08:00, 16:00 UTC
        # We check if this candle is ON or immediately AFTER the hour mark
        # Simple approach: Check if hour matches and we haven't processed this hour
        if ts.hour % 8 == 0 and ts.minute == 0:
            if self.last_funding_time == ts:
                return
            self.last_funding_time = ts
            
            # Calculate Funding Fee
            # Rate is Daily. Fee per interval = Daily / 3.
            position_value = self.current_position.quantity * self.current_position.current_price
            funding_fee = position_value * (self.config.funding_rate_daily / Decimal("3"))
            
            # Deduction logic:
            # If Rate > 0: Long Pays Short. (Long loses equity).
            # If Rate < 0: Short Pays Long. (Long gains equity).
            
            # Simplified: Assuming standard Positive funding market
            if self.current_position.direction == TradeDirection.LONG:
                if self.config.funding_rate_daily > 0:
                    self.equity -= funding_fee
                    logger.debug(f"Funding Fee Paid: -{funding_fee:.2f}")
                else:
                    self.equity += abs(funding_fee)
            else: # SHORT
                if self.config.funding_rate_daily > 0:
                    self.equity += funding_fee
                    logger.debug(f"Funding Fee Received: +{funding_fee:.2f}")
                else:
                    self.equity -= abs(funding_fee)

    def _check_liquidation(self, candle_high: Decimal, candle_low: Decimal) -> Optional[tuple]:
        """Check if position is liquidated based on leverage."""
        if not self.current_position:
            return None
            
        if self.config.leverage <= 1:
            return None
            
        pos = self.current_position
        # Maintenance Margin Rate (0.5%)
        maintenance_rate = Decimal("0.005")
        leverage = Decimal(self.config.leverage)
        
        # Calculate Liquidation Price automatically
        # Long Liq = Entry * (1 - 1/Lev + Maint)
        # Short Liq = Entry * (1 + 1/Lev - Maint)
        
        if pos.direction == TradeDirection.LONG:
            liq_price = pos.avg_entry_price * (Decimal("1") - (Decimal("1")/leverage) + maintenance_rate)
            if candle_low <= liq_price:
                # Ensure we don't return negative price
                return (max(Decimal("0"), liq_price), "LIQUIDATION")
                
        else: # SHORT
            liq_price = pos.avg_entry_price * (Decimal("1") + (Decimal("1")/leverage) - maintenance_rate)
            if candle_high >= liq_price:
                return (liq_price, "LIQUIDATION")
                
        return None

    def _check_sl_tp_trailing_with_high_low(
        self, 
        candle_high: Decimal, 
        candle_low: Decimal,
        candle_open: Optional[Decimal] = None,
    ) -> Optional[tuple]:
        """
        Level 2 SL/TP/Trailing Check with Price Path Assumption.
        
        Checks:
        1. Fixed Stop Loss
        2. Fixed Take Profit
        3. Trailing Stop (dynamic)
        4. Conflict resolution using price_path_assumption
        
        Args:
            candle_high: High price of the candle
            candle_low: Low price of the candle
            candle_open: Open price (for realistic assumption)
            
        Returns:
            Tuple (close_price, reason) if triggered, None otherwise
        """
        if not self.current_position:
            return None
        
        stop_loss = self.current_position.stop_loss
        take_profit = self.current_position.take_profit
        trailing_stop = self.current_position.trailing_stop_price
        
        if self.current_position.direction == TradeDirection.LONG:
            # LONG: SL/Trailing triggers on Low, TP triggers on High
            
            # Determine which can trigger
            sl_triggered = stop_loss and candle_low <= stop_loss
            trailing_triggered = trailing_stop and candle_low <= trailing_stop
            tp_triggered = take_profit and candle_high >= take_profit
            
            # Use worst SL (trailing or fixed)
            effective_sl = None
            sl_reason = None
            if sl_triggered and trailing_triggered:
                # Both triggered, use whichever is worse (lower for LONG)
                if trailing_stop < stop_loss:
                    effective_sl = trailing_stop
                    sl_reason = "Trailing Stop"
                else:
                    effective_sl = stop_loss
                    sl_reason = "Stop Loss"
            elif sl_triggered:
                effective_sl = stop_loss
                sl_reason = "Stop Loss"
            elif trailing_triggered:
                effective_sl = trailing_stop
                sl_reason = "Trailing Stop"
            
            # Spec-required: Handle TP/SL conflict with price_path_assumption
            if effective_sl and tp_triggered:
                # CONFLICT: Both can trigger in same candle
                assumption = self.config.price_path_assumption
                
                if assumption == "neutral":
                    # Conservative: SL before TP
                    logger.debug(f"TP/SL conflict (LONG): NEUTRAL → SL wins")
                    return (effective_sl, f"{sl_reason} (Neutral assumption)")
                
                elif assumption == "optimistic":
                    # Optimistic: TP before SL
                    logger.debug(f"TP/SL conflict (LONG): OPTIMISTIC → TP wins")
                    return (take_profit, "Take Profit (Optimistic assumption)")
                
                elif assumption == "realistic" and candle_open:
                    # Realistic: Based on candle open direction
                    if candle_open < self.current_position.avg_entry_price:
                        # Opened down → SL likely hit first
                        logger.debug(f"TP/SL conflict (LONG): REALISTIC (open down) → SL wins")
                        return (effective_sl, f"{sl_reason} (Realistic assumption)")
                    else:
                        # Opened up → TP likely hit first
                        logger.debug(f"TP/SL conflict (LONG): REALISTIC (open up) → TP wins")
                        return (take_profit, "Take Profit (Realistic assumption)")
                else:
                    # Fallback to neutral if realistic missing data
                    logger.debug(f"TP/SL conflict (LONG): Fallback to NEUTRAL")
                    return (effective_sl, f"{sl_reason} (Neutral fallback)")
            
            # No conflict: return whichever triggered
            if effective_sl:
                logger.debug(f"LONG {sl_reason} triggered: low={candle_low} <= {effective_sl}")
                return (effective_sl, sl_reason)
            if tp_triggered:
                logger.debug(f"LONG TP triggered: high={candle_high} >= tp={take_profit}")
                return (take_profit, "Take Profit")
        
        else:  # SHORT position
            # SHORT: SL/Trailing triggers on High, TP triggers on Low
            
            # Determine which can trigger
            sl_triggered = stop_loss and candle_high >= stop_loss
            trailing_triggered = trailing_stop and candle_high >= trailing_stop
            tp_triggered = take_profit and candle_low <= take_profit
            
            # Use worst SL (trailing or fixed)
            effective_sl = None
            sl_reason = None
            if sl_triggered and trailing_triggered:
                # Both triggered, use whichever is worse (higher for SHORT)
                if trailing_stop > stop_loss:
                    effective_sl = trailing_stop
                    sl_reason = "Trailing Stop"
                else:
                    effective_sl = stop_loss
                    sl_reason = "Stop Loss"
            elif sl_triggered:
                effective_sl = stop_loss
                sl_reason = "Stop Loss"
            elif trailing_triggered:
                effective_sl = trailing_stop
                sl_reason = "Trailing Stop"
            
            # Spec-required: Handle TP/SL conflict with price_path_assumption
            if effective_sl and tp_triggered:
                # CONFLICT: Both can trigger in same candle
                assumption = self.config.price_path_assumption
                
                if assumption == "neutral":
                    # Conservative: SL before TP
                    logger.debug(f"TP/SL conflict (SHORT): NEUTRAL → SL wins")
                    return (effective_sl, f"{sl_reason} (Neutral assumption)")
                
                elif assumption == "optimistic":
                    # Optimistic: TP before SL
                    logger.debug(f"TP/SL conflict (SHORT): OPTIMISTIC → TP wins")
                    return (take_profit, "Take Profit (Optimistic assumption)")
                
                elif assumption == "realistic" and candle_open:
                    # Realistic: Based on candle open direction
                    if candle_open > self.current_position.avg_entry_price:
                        # Opened up → SL likely hit first
                        logger.debug(f"TP/SL conflict (SHORT): REALISTIC (open up) → SL wins")
                        return (effective_sl, f"{sl_reason} (Realistic assumption)")
                    else:
                        # Opened down → TP likely hit first
                        logger.debug(f"TP/SL conflict (SHORT): REALISTIC (open down) → TP wins")
                        return (take_profit, "Take Profit (Realistic assumption)")
                else:
                    # Fallback to neutral
                    logger.debug(f"TP/SL conflict (SHORT): Fallback to NEUTRAL")
                    return (effective_sl, f"{sl_reason} (Neutral fallback)")
            
            # No conflict: return whichever triggered
            if effective_sl:
                logger.debug(f"SHORT {sl_reason} triggered: high={candle_high} >= {effective_sl}")
                return (effective_sl, sl_reason)
            if tp_triggered:
                logger.debug(f"SHORT TP triggered: low={candle_low} <= tp={take_profit}")
                return (take_profit, "Take Profit")
        
        return None
    
    def _check_sl_tp_with_high_low(
        self, 
        candle_high: Decimal, 
        candle_low: Decimal
    ) -> Optional[tuple]:
        """Legacy alias - redirects to new unified method."""
        # Note: candle_open defaults to None here (called from old code path)
        return self._check_sl_tp_trailing_with_high_low(candle_high, candle_low, None)
    
    def _should_close_position(self, current_price: Decimal) -> bool:
        """Legacy method - check if position should be closed (Close price only).
        
        Note: Prefer using _check_sl_tp_with_high_low for more accurate simulation.
        """
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
        """Calculate position size based on strategy configuration.
        
        Spec-required: Margin validation to prevent over-leveraging.
        """
        if self.config.position_sizing == PositionSizing.FIXED_QUANTITY:
            quantity = self.config.position_size_value
        elif self.config.position_sizing == PositionSizing.PERCENT_EQUITY:
            # Calculate max position value as % of equity
            max_position_value = self.equity * (self.config.position_size_value / Decimal("100"))
            quantity = max_position_value / price
        else:  # RISK_AMOUNT
            # Risk-based sizing (not fully implemented)
            max_risk = self.equity * (self.config.position_size_value / Decimal("100"))
            quantity = max_risk / price
        
        # Spec-required: Margin validation
        # Ensure position doesn't exceed available capital
        position_value = quantity * price
        available_capital = self.equity  # Simplified: could account for existing positions
        
        if position_value > available_capital:
            # Scale down to available capital
            quantity = available_capital / price
            logger.warning(f"Position size reduced due to insufficient capital: {quantity}")
        
        # Apply leverage if configured
        if self.config.leverage > 1:
            quantity = quantity * Decimal(str(self.config.leverage))
            
            # Double-check margin after leverage
            leveraged_value = quantity * price
            margin_required = leveraged_value / Decimal(str(self.config.leverage))
            if margin_required > available_capital:
                # Reduce to max leverage capacity
                max_quantity = (available_capital * Decimal(str(self.config.leverage))) / price
                quantity = max_quantity
                logger.warning(f"Leveraged position capped at available margin: {quantity}")
        
        return quantity
    
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
