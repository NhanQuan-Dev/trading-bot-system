"""Backtesting engine for strategy simulation."""

import logging
from decimal import Decimal
from typing import List, Dict, Optional, Callable, Union, Any
from datetime import datetime, timedelta
from uuid import UUID
import asyncio

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
    PositionSizing,
)
from .metrics_calculator import MetricsCalculator
from .market_simulator import MarketSimulator
from .timeframe_utils import resample_candles_to_htf, get_candles_in_htf_window, get_next_htf_window_candles, MultiTimeframeContext

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
        # Ensure numeric config fields are Decimal for calculation safety
        self.config = self._ensure_decimal_config(config)
        
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        self.market_simulator = market_simulator or MarketSimulator(
            slippage_model=self.config.slippage_model,
            slippage_percent=self.config.slippage_percent,
            commission_model=self.config.commission_model,
            commission_rate=self.config.commission_percent,
            use_bid_ask_spread=self.config.use_bid_ask_spread if hasattr(self.config, 'use_bid_ask_spread') else False,
            spread_percent=self.config.spread_percent if hasattr(self.config, 'spread_percent') else Decimal("0.05"),
            market_fill_policy=self.config.market_fill_policy,
            limit_fill_policy=self.config.limit_fill_policy,
        )
        logger.info(f"ENGINE INITIALIZED: Leverage: {self.config.leverage}, HTF: {self.config.signal_timeframe}")

        # State
        self.equity = self.config.initial_capital
        self.peak_equity = self.config.initial_capital
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
        self.last_funding_time: Optional[datetime] = None
        self.total_bars_processed = 0
        self.signals_generated = 0

    def _ensure_decimal_config(self, config: BacktestConfig) -> BacktestConfig:
        """Convert float config fields to Decimal for safety using dataclasses.replace."""
        import dataclasses
        fields_to_convert = [
            'initial_capital', 'slippage_percent', 'commission_percent',
            'taker_fee_rate', 'maker_fee_rate', 'funding_rate_daily',
            'margin_requirement', 'position_size_value', 'leverage'
        ]
        
        changes = {}
        for field in fields_to_convert:
            if hasattr(config, field):
                val = getattr(config, field)
                if val is not None:
                    try:
                        changes[field] = Decimal(str(val))
                    except (ValueError, TypeError):
                        pass
        
        if changes:
             return dataclasses.replace(config, **changes)
        return config
    
    def _emit_event(
        self,
        event_type: BacktestEventType,
        details: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        trade_id: Optional[UUID] = None,
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
            trade_id=trade_id,
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
        
        logger.info(f"Starting backtest run: id={backtest_run.id}, candles={len(candles)}")
        
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
            # 0. Pre-process Timestamps (Optimize Speed)
            # Parse all timestamps once to avoid repeated parsing in loops
            if candles and isinstance(candles[0]["timestamp"], str):
                for c in candles:
                     c["timestamp"] = datetime.fromisoformat(c["timestamp"])
            
            # New: Pre-calculation hook for vectorized strategies (single-tf fallback)
            is_multi_tf = (self.config.signal_timeframe != "1m") or (self.config.condition_timeframes)
            if not is_multi_tf and hasattr(strategy_func, "pre_calculate"):
                logger.info("Executing strategy pre-calculation (Vectorized Mode - Single TF)...")
                try:
                    strategy_func.pre_calculate(candles)
                except Exception as e:
                    logger.error(f"Engine failed to call strategy pre_calculate: {e}")
            
            # Spec-required: Multi-timeframe processing
            # We enter this block if using HTF signals OR if condition_timeframes are required
            is_multi_tf = (self.config.signal_timeframe != "1m") or (self.config.condition_timeframes)

            if is_multi_tf:
                logger.info(f"Multi-timeframe mode active. Signal={self.config.signal_timeframe}, Conditions={self.config.condition_timeframes}")
                
                 # 1. Gather all required timeframes
                required_tfs = set()
                if self.config.signal_timeframe != "1m":
                    required_tfs.add(self.config.signal_timeframe)
                if self.config.condition_timeframes:
                    required_tfs.update(self.config.condition_timeframes)
                required_tfs.discard("1m")
                htf_data_maps = {}
                htf_intervals = {}
                htf_candles_for_strategy = {}
                
                from .timeframe_utils import TIMEFRAME_MINUTES
                for tf in required_tfs:
                    resampled = resample_candles_to_htf(candles, tf)
                    htf_candles_for_strategy[tf] = resampled # List for pre_calculate
                    htf_data_maps[tf] = {}
                    for c in resampled:
                         ts = c["timestamp"]
                         # Normalize to UTC timestamp for reliable comparison
                         htf_data_maps[tf][int(ts.timestamp())] = c
                    htf_intervals[tf] = TIMEFRAME_MINUTES[tf]
                    logger.debug(f"Prepared {len(resampled)} candles for {tf}")

                # New: Pre-calculation hook for vectorized strategies (multi-tf supported)
                if hasattr(strategy_func, "pre_calculate"):
                    logger.info("Executing strategy pre-calculation (Vectorized Mode)...")
                    try:
                        strategy_func.pre_calculate(candles, htf_candles=htf_candles_for_strategy)
                    except Exception as e:
                        logger.error(f"Engine failed to call strategy pre_calculate: {e}")

                # Context State
                # current_closed_candles: The latest COMPLETE candle for each TF
                current_closed_candles = {tf: None for tf in required_tfs}
                # history_containers: Rolling history for each TF
                history_containers = {tf: [] for tf in required_tfs} 

                # State tracking
                pending_signal = None 
                execution_delay_counter = 0
                last_signal_evaluated_ts = None
                
                # Signal TF Interval (if not 1m)
                signal_tf_interval = None
                if self.config.signal_timeframe != "1m":
                     signal_tf_interval = TIMEFRAME_MINUTES[self.config.signal_timeframe]

                total_candles = len(candles)
                logger.debug(f"Starting Multi-TF loop with {total_candles} 1m candles")
                
                # Iterate through ALL 1m candles
                for idx, m1_candle in enumerate(candles):
                    self.total_bars_processed += 1
                    
                    # Get candle timestamp
                    m1_timestamp = m1_candle["timestamp"]
                    
                    m1_unix = int(m1_timestamp.timestamp())
                    
                    # Update Context for ALL TFs
                    # We check if we just crossed a boundary for any TF
                    for tf in required_tfs:
                        interval = htf_intervals[tf]
                        # Calc which window corresponds to current time
                        # Usually: floor(time / interval) * interval
                        # When a window CLOSES, we are in the NEXT window.
                        current_window_start = (m1_unix // (interval * 60)) * (interval * 60)
                        
                        # The candle that JUST closed starts at (current - interval)
                        prev_window_start = current_window_start - (interval * 60)
                        
                        # Check if we have that candle (meaning it just closed or is closed)
                        if prev_window_start in htf_data_maps[tf]:
                            cand = htf_data_maps[tf][prev_window_start]
                            
                            # If this is different from what we knew, it means a new candle closed
                            # Or we are just initializing
                            if current_closed_candles[tf] != cand:
                                current_closed_candles[tf] = cand
                                history_containers[tf].append(cand)
                                # Note: No longer capping history to 200. Strategies can access full history.

                    # Determine Trigger
                    should_trigger = False
                    trigger_candle = m1_candle # Default to 1m
                    trigger_idx = idx
                    
                    if self.config.signal_timeframe == "1m":
                        should_trigger = True
                    else:
                        # HTF Signal Mode: Only trigger on boundary crossing
                        # Use the same logic as Context Update, but specifically for Signal TF
                        interval = signal_tf_interval
                        current_window_start = (m1_unix // (interval * 60)) * (interval * 60)
                        prev_window_start = current_window_start - (interval * 60)
                        
                        if last_signal_evaluated_ts != prev_window_start and prev_window_start in htf_data_maps[self.config.signal_timeframe]:
                            should_trigger = True
                            trigger_candle = htf_data_maps[self.config.signal_timeframe][prev_window_start]
                            last_signal_evaluated_ts = prev_window_start
                            trigger_idx = idx # Pass 1m index for pre-calculated indicator lookup
                            
                            # Emit HTF Candle Event
                            self._emit_event(
                                BacktestEventType.HTF_CANDLE_CLOSED,
                                {
                                    "timeframe": self.config.signal_timeframe,
                                    "close": trigger_candle["close"],
                                    "timestamp": trigger_candle["timestamp"]
                                },
                                m1_timestamp
                            )
                    
                    # Generate and Handle Signal
                    if should_trigger:
                        # Build Context
                        # Note: We pass copies to avoid mutation risks if strategy relies on them
                        ctx = MultiTimeframeContext(
                            current_candles=current_closed_candles.copy(),
                            history={k: v[:] for k, v in history_containers.items()} # Shallow copy of lists
                        )
                        
                        htf_signal = strategy_func(trigger_candle, trigger_idx, self.current_position, multi_tf_context=ctx)
                        
                        if htf_signal:
                            self.signals_generated += 1
                            logger.debug(f"Signal #{self.signals_generated} at {m1_timestamp}: {htf_signal['type']}")
                            pending_signal = htf_signal
                    
                    # Process pending signal with Execution Delay support
                    if pending_signal:
                        if self.config.execution_delay_bars > 0:
                            if execution_delay_counter >= self.config.execution_delay_bars:
                                self._process_signal(pending_signal, m1_candle)
                                pending_signal = None
                                execution_delay_counter = 0
                            else:
                                execution_delay_counter += 1
                        else:
                            self._process_signal(pending_signal, m1_candle)
                            pending_signal = None
                    
                    # NEW: Call strategy on EVERY 1m candle when position exists
                    # This allows strategies to react to price changes (e.g., Margin Defense at -70% ROI)
                    # BEFORE liquidation check happens
                    if self.current_position and not should_trigger:
                        # Build context for position management signals
                        ctx = MultiTimeframeContext(
                            current_candles=current_closed_candles.copy(),
                            history={k: v[:] for k, v in history_containers.items()}
                        )
                        pos_signal = strategy_func(m1_candle, idx, self.current_position, multi_tf_context=ctx)
                        if pos_signal:
                            self.signals_generated += 1
                            logger.debug(f"Position mgmt signal at {m1_timestamp}: {pos_signal['type']}")
                            self._process_signal(pos_signal, m1_candle)
                    
                    # ALWAYS check SL/TP/Liquidation on EVERY 1m candle (Shared Logic)
                    if self.current_position:
                        # ... (Same SL/TP Logic as before) ...
                        # Define high/low early
                        candle_high = Decimal(str(m1_candle.get("high", m1_candle["close"])))
                        candle_low = Decimal(str(m1_candle.get("low", m1_candle["close"])))
                        candle_open = Decimal(str(m1_candle.get("open", m1_candle["close"])))
                        current_price = Decimal(str(m1_candle["close"]))
                        
                        self.current_position.update_unrealized_pnl(current_price)
                        
                         # Track MAE/MFE
                        if self.current_position.direction == TradeDirection.LONG:
                            mfe_price = candle_high
                            mae_price = candle_low
                        else:
                            mfe_price = candle_low
                            mae_price = candle_high
                            
                        # Calculate unrealized ROE for these extremes (Inline optimization)
                        def calc_roe(price):
                            if self.current_position.direction == TradeDirection.LONG:
                                diff = price - self.current_position.avg_entry_price
                            else:
                                diff = self.current_position.avg_entry_price - price
                            entry_value = self.current_position.avg_entry_price * self.current_position.quantity
                            if entry_value <= 0: return Decimal("0")
                            pnl = diff * self.current_position.quantity
                            initial_margin = entry_value / self.config.leverage
                            return (pnl / initial_margin) * Decimal("100")
                            
                        current_mae_roe = calc_roe(mae_price)
                        current_mfe_roe = calc_roe(mfe_price)
                        
                        if current_mae_roe < self.current_trade_max_drawdown:
                            self.current_trade_max_drawdown = current_mae_roe
                        if current_mfe_roe > self.current_trade_max_runup:
                            self.current_trade_max_runup = current_mfe_roe
                        
                        # Update trailing stop
                        self.current_position.update_trailing_stop(candle_high, candle_low)
                        
                        # Liquidation Check
                        liquidation_result = self._check_liquidation(candle_high, candle_low)
                        if liquidation_result:
                            close_price, reason = liquidation_result
                            logger.warning(f"LIQUIDATION Triggered: {reason}")
                            self._close_position(price=close_price, timestamp=m1_candle["timestamp"], reason=reason)
                        else:
                            # SL/TP Check
                            sl_tp_result = self._check_sl_tp_trailing_with_high_low(candle_high, candle_low, candle_open)
                            if sl_tp_result:
                                close_price, reason = sl_tp_result
                                logger.debug(f"SL/TP HIT: {reason}")
                                self._close_position(
                                    price=close_price,
                                    timestamp=m1_candle["timestamp"],
                                    reason=reason,
                                    candle_high=candle_high,
                                    candle_low=candle_low,
                                    candle_open=candle_open,
                                )
                    
                    # Update Equity Curve
                    # OPTIMIZATION: Downsample to hourly resolution to save ~25% runtime
                    if idx % 60 == 0 or idx == len(candles) - 1:
                        self._update_equity_curve(m1_candle["timestamp"], Decimal(str(m1_candle["close"])))
                    
                    self._check_funding(m1_candle)
                    
                    # Progress update
                    if progress_callback and idx % max(100, int(total_candles / 100)) == 0:
                        percent = int((idx / total_candles) * 100)
                        backtest_run.update_progress(percent)
                        await progress_callback(percent)
                    if idx % 100 == 0:
                        await asyncio.sleep(0)
                
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
                    
                    # Yield control to event loop periodically to prevent blocking
                    if idx % 100 == 0:
                        await asyncio.sleep(0)
            
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
                equity_curve=self._downsample_equity_curve(self.equity_curve),
                trades=self.trades,
                events=self.events,
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
        
        # Define high/low early for use in all checks
        candle_high = Decimal(str(candle.get("high", candle["close"])))
        candle_low = Decimal(str(candle.get("low", candle["close"])))

        if self.current_position:
            self.current_position.update_unrealized_pnl(current_price)
            
            # Track MAE/MFE (Max Adverse/Favorable Excursion) with 1m precision (ROE Percentage)
            # We use candle_high and candle_low for intra-minute extreme capture
            if self.current_position.direction == TradeDirection.LONG:
                mfe_price = candle_high
                mae_price = candle_low
            else:
                mfe_price = candle_low
                mae_price = candle_high
                
            def calc_roe(price):
                if self.current_position.direction == TradeDirection.LONG:
                    diff = price - self.current_position.avg_entry_price
                else:
                    diff = self.current_position.avg_entry_price - price
                
                # Leverage-adjusted ROE (Return on Margin)
                pnl = diff * self.current_position.quantity
                entry_value = self.current_position.avg_entry_price * self.current_position.quantity
                
                if entry_value <= 0:
                    return Decimal("0")
                
                # Formula: (pnl / (notional / leverage)) * 100
                leverage = Decimal(str(self.config.leverage))
                return (pnl / (entry_value / leverage)) * Decimal("100")
                
            current_mae_roe = calc_roe(mae_price)
            current_mfe_roe = calc_roe(mfe_price)
            
            if current_mae_roe < self.current_trade_max_drawdown:
                self.current_trade_max_drawdown = current_mae_roe
            if current_mfe_roe > self.current_trade_max_runup:
                self.current_trade_max_runup = current_mfe_roe
            
            # Level 2 SL/TP Check: Use High/Low prices for more accurate simulation
            # (Variables already defined above)
            
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
                    candle_low=candle_low,
                    candle_high=candle_high,
                    candle_open=candle_open,
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
    
    def _downsample_equity_curve(self, equity_curve: List[EquityCurvePoint], max_points: int = 5000) -> List[EquityCurvePoint]:
        """Downsample equity curve to avoid database overload."""
        if not equity_curve or len(equity_curve) <= max_points:
            return equity_curve
            
        step = len(equity_curve) / max_points
        return [equity_curve[int(i * step)] for i in range(max_points)]

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
        - update_levels: Update SL/TP/Trailing for existing position
        """
        signal_type = signal.get("type")
        signal_quantity = signal.get("quantity")  # Optional quantity override
        current_price = Decimal(str(candle["close"]))
        timestamp = candle["timestamp"]
        
        # === OPEN NEW POSITIONS (from flat) ===
        if signal_type in ("open_long", "buy", "ENTRY_LONG") and not self.current_position:
            self._open_long_position(price=current_price, timestamp=timestamp, signal=signal, candle=candle)
        
        elif signal_type in ("open_short", "sell", "ENTRY_SHORT") and not self.current_position:
            self._open_short_position(price=current_price, timestamp=timestamp, signal=signal, candle=candle)
        
        # === ADD TO EXISTING POSITIONS (scale in) ===
        elif signal_type == "add_long" and self._is_long():
            self._add_to_position(price=current_price, timestamp=timestamp, quantity=signal_quantity, signal=signal)
        
        elif signal_type == "add_short" and self._is_short():
            self._add_to_position(price=current_price, timestamp=timestamp, quantity=signal_quantity, signal=signal)
        
        # === UPDATE TP/SL/TRAILING ===
        elif signal_type == "update_levels" and self.current_position:
            # Update stop loss if provided
            if "stop_loss" in signal:
                new_sl = signal["stop_loss"]
                self.current_position.stop_loss = Decimal(str(new_sl)) if new_sl is not None else None
                logger.debug(f"Updated SL to {self.current_position.stop_loss}")
            
            # Update take profit if provided
            if "take_profit" in signal:
                new_tp = signal["take_profit"]
                self.current_position.take_profit = Decimal(str(new_tp)) if new_tp is not None else None
                logger.debug(f"Updated TP to {self.current_position.take_profit}")
            
            # Update trailing stop if provided
            if "trailing_stop_percent" in signal:
                new_trailing = signal["trailing_stop_percent"]
                self.current_position.trailing_stop_percent = Decimal(str(new_trailing)) if new_trailing is not None else None
                logger.debug(f"Updated Trailing Stop to {self.current_position.trailing_stop_percent}%")
            
            # Emit LEVELS_UPDATED event
            self._emit_event(
                event_type=BacktestEventType.LEVELS_UPDATED,
                details={
                    "stop_loss": float(self.current_position.stop_loss) if self.current_position.stop_loss else None,
                    "take_profit": float(self.current_position.take_profit) if self.current_position.take_profit else None,
                    "trailing_stop_percent": float(self.current_position.trailing_stop_percent) if self.current_position.trailing_stop_percent else None,
                    "reason": "Signal Update"
                },
                timestamp=timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
                trade_id=self.current_position.id if hasattr(self.current_position, 'id') else None
            )
        
        # === UPDATE MARGIN ===
        elif signal_type == "update_margin" and self.current_position:
            self._update_margin(signal, timestamp)
        
        # === CLOSE ENTIRE POSITION ===
        elif signal_type in ("close_position", "close", "EXIT_LONG", "EXIT_SHORT") and self.current_position:
            reason = signal.get("metadata", {}).get("reason") if isinstance(signal.get("metadata"), dict) else (signal.get("metadata") or "Signal close")
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
            self._open_long_position(price=current_price, timestamp=timestamp, signal=signal, candle=candle)
        
        elif signal_type == "flip_short" and self._is_long():
            self._close_position(price=current_price, timestamp=timestamp, reason="Flip to SHORT")
            self._open_short_position(price=current_price, timestamp=timestamp, signal=signal, candle=candle)
    
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
        candle: Dict = None,  # Added: candle data for limit order fill detection
    ) -> None:
        """Open long position."""
        
        if signal.get("quantity") and float(signal["quantity"]) > 0:
            quantity = Decimal(str(signal["quantity"]))
            sizing_source = "STRATEGY"
        else:
            quantity = self._calculate_position_size(price)
            sizing_source = "ENGINE"
        
        # Extract limit price from signal if provided
        limit_price = signal.get("limit_price")
        if limit_price is not None:
            limit_price = Decimal(str(limit_price))
        
        # Extract candle high/low for limit order fill detection
        candle_low = None
        candle_high = None
        if candle:
            candle_low = Decimal(str(candle.get("low", price)))
            candle_high = Decimal(str(candle.get("high", price)))
        
        # Simulate LONG entry (supports both market and limit orders)
        # print(f"DEBUG: Processing Signal (MODIFIED_TEST): {signal}")
        fill = self.market_simulator.simulate_long_entry(
            symbol=self.config.symbol,
            quantity=quantity,
            current_price=price,
            timestamp=timestamp,
            limit_price=limit_price,
            candle_low=candle_low,
            candle_high=candle_high,
        )
        
        # Override commission with Taker Fee
        trade_value = fill.filled_quantity * fill.filled_price
        fill.commission = trade_value * self.config.taker_fee_rate
        
        if fill.filled_quantity == 0:
            return  # Order not filled
        
        leverage = Decimal(str(self.config.leverage))
        margin_value = (fill.filled_price * fill.filled_quantity) / leverage
        
        # Create position
        self.current_position = BacktestPosition(
            symbol=self.config.symbol,
            direction=TradeDirection.LONG,
            quantity=fill.filled_quantity,
            avg_entry_price=fill.filled_price,
            initial_entry_price=fill.filled_price,  # Store initial entry
            initial_quantity=fill.filled_quantity,  # Store initial quantity
            isolated_margin=margin_value, # Set initial isolated margin
        )
        # Store stop loss/take profit from signal (if provided)
        provided_sl = signal.get("stop_loss")
        provided_tp = signal.get("take_profit")
        provided_sl_pct = signal.get("stop_loss_percent")
        provided_tp_pct = signal.get("take_profit_percent")
        
        leverage = Decimal(str(self.config.leverage))
        
        # ROI-based SL/TP Conversion
        if provided_sl_pct is not None:
            # LONG SL: Price = Entry * (1 - (ROI_Pct / 100 / Leverage))
            # ROI is positive magnitude, but we subtract for SL
            sl_roi = Decimal(str(provided_sl_pct))
            self.current_position.stop_loss = fill.filled_price * (Decimal("1") - (sl_roi / Decimal("100") / leverage))
        elif provided_sl:
            self.current_position.stop_loss = Decimal(str(provided_sl))
            
        if provided_tp_pct is not None:
            # LONG TP: Price = Entry * (1 + (ROI_Pct / 100 / Leverage))
            tp_roi = Decimal(str(provided_tp_pct))
            self.current_position.take_profit = fill.filled_price * (Decimal("1") + (tp_roi / Decimal("100") / leverage))
        elif provided_tp:
            self.current_position.take_profit = Decimal(str(provided_tp))
            
        self.current_position.entry_time = timestamp
        self.current_position.entry_commission = fill.commission
        
        # Prepare Metadata (Ensure it's a Dict)
        raw_metadata = signal.get("metadata", signal.get("reason"))
        if isinstance(raw_metadata, dict):
            metadata = raw_metadata.copy()
        elif isinstance(raw_metadata, str):
            metadata = {"reason": raw_metadata}
        else:
            metadata = {}
            
        metadata["sizing_source"] = sizing_source
        metadata["initial_margin"] = float(margin_value)
        metadata["current_margin"] = float(margin_value)
        
        self.current_position.metadata = metadata
        
        logger.debug(f"POSITION OPENED: TP={self.current_position.take_profit}, SL={self.current_position.stop_loss}, Entry={self.current_position.avg_entry_price}, Source={sizing_source}")
        
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
            trade_id=self.current_position.id
        )
        
        logger.debug(f"Opened LONG: {fill.filled_quantity} @ {fill.filled_price}")
    
    def _open_short_position(
        self,
        price: Decimal,
        timestamp: str,
        signal: Dict,
        candle: Dict = None,  # Added: candle data for limit order fill detection
    ) -> None:
        """Open short position."""
        
        if signal.get("quantity") and float(signal["quantity"]) > 0:
            quantity = Decimal(str(signal["quantity"]))
            sizing_source = "STRATEGY"
        else:
            quantity = self._calculate_position_size(price)
            sizing_source = "ENGINE"
        
        # Extract limit price from signal if provided
        limit_price = signal.get("limit_price")
        if limit_price is not None:
            limit_price = Decimal(str(limit_price))
        
        # Extract candle high/low for limit order fill detection
        candle_low = None
        candle_high = None
        if candle:
            candle_low = Decimal(str(candle.get("low", price)))
            candle_high = Decimal(str(candle.get("high", price)))
        
        # Simulate SHORT entry (supports both market and limit orders)
        fill = self.market_simulator.simulate_short_entry(
            symbol=self.config.symbol,
            quantity=quantity,
            current_price=price,
            timestamp=timestamp,
            limit_price=limit_price,
            candle_low=candle_low,
            candle_high=candle_high,
        )
        
        # Override commission with Taker Fee
        trade_value = fill.filled_quantity * fill.filled_price
        fill.commission = trade_value * self.config.taker_fee_rate
        
        if fill.filled_quantity == 0:
            return
        
        leverage = Decimal(str(self.config.leverage))
        margin_value = (fill.filled_price * fill.filled_quantity) / leverage

        # Create position
        self.current_position = BacktestPosition(
            symbol=self.config.symbol,
            direction=TradeDirection.SHORT,
            quantity=fill.filled_quantity,
            avg_entry_price=fill.filled_price,
            initial_entry_price=fill.filled_price,  # Store initial entry
            initial_quantity=fill.filled_quantity,  # Store initial quantity
            isolated_margin=margin_value, # Set initial isolated margin
        )
        # Store stop loss/take profit from signal (if provided)
        provided_sl = signal.get("stop_loss")
        provided_tp = signal.get("take_profit")
        provided_sl_pct = signal.get("stop_loss_percent")
        provided_tp_pct = signal.get("take_profit_percent")
        
        leverage = Decimal(str(self.config.leverage))
        
        # ROI-based SL/TP Conversion (SHORT)
        if provided_sl_pct is not None:
            # SHORT SL: Price = Entry * (1 + (ROI_Pct / 100 / Leverage))
            # SL is ABOVE entry for SHORT
            sl_roi = Decimal(str(provided_sl_pct))
            self.current_position.stop_loss = fill.filled_price * (Decimal("1") + (sl_roi / Decimal("100") / leverage))
            
        elif provided_sl:
            self.current_position.stop_loss = Decimal(str(provided_sl))
            
        if provided_tp_pct is not None:
            # SHORT TP: Price = Entry * (1 - (ROI_Pct / 100 / Leverage))
            tp_roi = Decimal(str(provided_tp_pct))
            self.current_position.take_profit = fill.filled_price * (Decimal("1") - (tp_roi / Decimal("100") / leverage))
            
        elif provided_tp:
            self.current_position.take_profit = Decimal(str(provided_tp))
            
        self.current_position.entry_time = timestamp
        self.current_position.entry_commission = fill.commission
        
        # Prepare Metadata (Ensure it's a Dict)
        raw_metadata = signal.get("metadata", signal.get("reason"))
        if isinstance(raw_metadata, dict):
            metadata = raw_metadata.copy()
        elif isinstance(raw_metadata, str):
            metadata = {"reason": raw_metadata}
        else:
            metadata = {}
            
        metadata["sizing_source"] = sizing_source
        metadata["initial_margin"] = float(margin_value)
        metadata["current_margin"] = float(margin_value)
        
        self.current_position.metadata = metadata
            
        logger.debug(f"POSITION OPENED: TP={self.current_position.take_profit}, SL={self.current_position.stop_loss}, Entry={self.current_position.avg_entry_price}, Source={sizing_source}")
        
        # Note: Don't modify equity when opening position
        # Equity will be updated when position is closed with realized PnL
        
        logger.debug(f"Opened SHORT: {fill.filled_quantity} @ {fill.filled_price}")
        
        # Emit event
        self._emit_event(
            BacktestEventType.TRADE_OPENED,
            {
                "direction": "SHORT",
                "price": float(fill.filled_price),
                "quantity": float(fill.filled_quantity),
                "stop_loss": float(self.current_position.stop_loss) if self.current_position.stop_loss else None,
                "take_profit": float(self.current_position.take_profit) if self.current_position.take_profit else None,
                "commission": float(fill.commission),
                "fill_conditions": fill.fill_conditions_met,
            },
            timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            trade_id=self.current_position.id
        )
    
    def _close_position(
        self,
        price: Decimal,
        timestamp: str,
        reason: Union[str, Dict[str, Any]],
        candle_low: Optional[Decimal] = None,
        candle_high: Optional[Decimal] = None,
        candle_open: Optional[Decimal] = None,
    ) -> None:
        """Close current position and record trade."""
        if not self.current_position:
            return
        
        # Prepare reason string for policy check
        if isinstance(reason, dict):
            r_str = str(reason.get("reason", "")).lower()
        else:
            r_str = str(reason).lower()
            
        # Simulate position exit
        if self.current_position.direction == TradeDirection.LONG:
            # Closing LONG = SHORT entry action
            fill = self.market_simulator.simulate_short_entry(
                symbol=self.config.symbol,
                quantity=self.current_position.quantity,
                current_price=price,
                timestamp=timestamp,
                limit_price=price if "take profit" in r_str or "tp" in r_str or "stop loss" in r_str or "sl" in r_str else None,
                candle_low=candle_low,
                candle_high=candle_high,
                candle_open=candle_open,
            )
        else:
            # Closing SHORT = LONG entry action
            fill = self.market_simulator.simulate_long_entry(
                symbol=self.config.symbol,
                quantity=self.current_position.quantity,
                current_price=price,
                timestamp=timestamp,
                limit_price=price if "take profit" in r_str or "tp" in r_str or "stop loss" in r_str or "sl" in r_str else None,
                candle_low=candle_low,
                candle_high=candle_high,
                candle_open=candle_open,
            )
            
        # Override commission based on Maker/Taker
        is_maker = False
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
        funding_fee = getattr(self.current_position, 'accumulated_funding', Decimal("0"))
        
        total_costs = entry_commission + fill.commission + fill.slippage + funding_fee
        net_pnl = pnl - total_costs
        
        # Calculate Fee Breakdown
        # Entry assumed Taker (default engine behavior)
        taker_fee = entry_commission
        maker_fee = Decimal("0")
        
        if is_maker:
            maker_fee += fill.commission
        else:
            taker_fee += fill.commission
            
        # Update equity with net P&L
        self.equity += net_pnl
        
        entry_value = self.current_position.avg_entry_price * fill.filled_quantity
        # ROI calculation (Binance Style: Return on Margin)
        # ROI% = (Net PnL / Initial Margin) * 100
        # Initial Margin = Notional / Leverage
        if entry_value > 0:
            leverage = Decimal(str(self.config.leverage)) if self.config.leverage else Decimal("1")
            initial_margin = entry_value / leverage
            pnl_percent = (net_pnl / initial_margin) * Decimal("100")
        else:
            pnl_percent = Decimal("0")
        
        # Normalize exit reason to dict
        exit_reason_dict = reason if isinstance(reason, dict) else {"reason": reason}

        # Spec-required: Calculate execution delay
        entry_time_dt = self.current_position.entry_time if isinstance(self.current_position.entry_time, datetime) else datetime.fromisoformat(self.current_position.entry_time)
        execution_delay_seconds = None
        if self.current_trade_signal_time:
            execution_delay_seconds = (entry_time_dt - self.current_trade_signal_time).total_seconds()

        # Create trade record
        trade = BacktestTrade(
            id=self.current_position.id,
            symbol=self.config.symbol,
            direction=self.current_position.direction,
            entry_time=entry_time_dt,
            entry_price=self.current_position.avg_entry_price,
            entry_quantity=fill.filled_quantity,
            entry_commission=entry_commission,
            entry_slippage=Decimal("0"), 
            # Initial entry tracking
            initial_entry_price=getattr(self.current_position, 'initial_entry_price', self.current_position.avg_entry_price),
            initial_entry_quantity=getattr(self.current_position, 'initial_quantity', fill.filled_quantity),
            exit_time=timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            exit_price=fill.filled_price,
            exit_quantity=fill.filled_quantity,
            exit_commission=fill.commission,
            exit_slippage=fill.slippage,
            gross_pnl=pnl,
            net_pnl=net_pnl,
            pnl_percent=pnl_percent,
            entry_reason=getattr(self.current_position, 'metadata', None),
            exit_reason=exit_reason_dict,
            # Spec-required fields
            signal_time=self.current_trade_signal_time,
            execution_delay_seconds=execution_delay_seconds,
            max_drawdown=self.current_trade_max_drawdown,
            max_runup=self.current_trade_max_runup,
            mae=self.current_trade_max_drawdown, 
            mfe=self.current_trade_max_runup,   
            fill_policy_used=self.current_trade_fill_policy,
            fill_conditions_met=self.current_trade_fill_conditions,
            # Fee Breakdown
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            funding_fee=funding_fee
        )
        print(f"DEBUG: Created BacktestTrade with exit_reason: {trade.exit_reason}")
        # Trade is complete - no need to call close()
        
        self.trades.append(trade)
        self.current_position = None
        
        # Reset intra-trade extremes
        if hasattr(self, 'current_trade_min_price'):
            delattr(self, 'current_trade_min_price')
        if hasattr(self, 'current_trade_max_price'):
            delattr(self, 'current_trade_max_price')
        
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
            trade_id=trade.id
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
        signal: Optional[Dict] = None,
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
        
        # PROPAGATE TP/SL UPDATES IF PROVIDED IN SIGNAL
        if signal:
            leverage = Decimal(str(self.config.leverage))
            
            # SL Updates
            if "stop_loss_percent" in signal:
                sl_roi = Decimal(str(signal["stop_loss_percent"]))
                if self.current_position.direction == TradeDirection.LONG:
                    self.current_position.stop_loss = self.current_position.avg_entry_price * (Decimal("1") - (sl_roi / Decimal("100") / leverage))
                else:
                    self.current_position.stop_loss = self.current_position.avg_entry_price * (Decimal("1") + (sl_roi / Decimal("100") / leverage))
                logger.debug(f"Scale-in updated SL (ROI%): {self.current_position.stop_loss}")
            elif "stop_loss" in signal:
                sl = signal["stop_loss"]
                self.current_position.stop_loss = Decimal(str(sl)) if sl is not None else self.current_position.stop_loss
                logger.debug(f"Scale-in updated SL: {self.current_position.stop_loss}")
            
            # TP Updates
            if "take_profit_percent" in signal:
                tp_roi = Decimal(str(signal["take_profit_percent"]))
                if self.current_position.direction == TradeDirection.LONG:
                    self.current_position.take_profit = self.current_position.avg_entry_price * (Decimal("1") + (tp_roi / Decimal("100") / leverage))
                else:
                    self.current_position.take_profit = self.current_position.avg_entry_price * (Decimal("1") - (tp_roi / Decimal("100") / leverage))
                logger.debug(f"Scale-in updated TP (ROI%): {self.current_position.take_profit}")
            elif "take_profit" in signal:
                tp = signal["take_profit"]
                self.current_position.take_profit = Decimal(str(tp)) if tp is not None else self.current_position.take_profit
                logger.debug(f"Scale-in updated TP: {self.current_position.take_profit}")

            if "trailing_stop_percent" in signal:
                trail = signal["trailing_stop_percent"]
                self.current_position.trailing_stop_percent = Decimal(str(trail)) if trail is not None else self.current_position.trailing_stop_percent
                logger.debug(f"Scale-in updated TR: {self.current_position.trailing_stop_percent}")

        # Update Margin in Metadata
        if self.current_position.metadata is None:
            self.current_position.metadata = {}
        
        leverage = Decimal(str(self.config.leverage))
        current_margin = (self.current_position.avg_entry_price * self.current_position.quantity) / leverage
        self.current_position.metadata["current_margin"] = float(current_margin)

        # Emit scale-in event
        self._emit_event(
            event_type=BacktestEventType.SCALE_IN,
            details={
                "price": float(fill.filled_price),
                "quantity": float(fill.filled_quantity),
                "total_qty": float(total_qty),
                "new_avg_price": float(new_avg_price),
                "commission": float(fill.commission),
                "reason": "Scale In"
            },
            timestamp=fill.fill_time if isinstance(fill.fill_time, datetime) else (datetime.fromisoformat(fill.fill_time) if isinstance(fill.fill_time, str) else datetime.utcnow()),
            trade_id=self.current_position.id if hasattr(self.current_position, 'id') else None
        )

        logger.debug(
            f"Added to {self.current_position.direction.value}: "
            f"+{fill.filled_quantity} @ {fill.filled_price}, "
            f"total qty: {total_qty}, avg price: {new_avg_price}, "
            f"new margin: {current_margin}"
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
        
        # Emit partial close event
        self._emit_event(
            event_type=BacktestEventType.PARTIAL_CLOSE,
            details={
                "price": float(fill.filled_price),
                "quantity": float(fill.filled_quantity),
                "remaining_qty": float(self.current_position.quantity - fill.filled_quantity),
                "pnl": float(net_pnl),
                "reason": exit_reason_dict.get("reason", "Partial Close")
            },
            timestamp=fill.fill_time if isinstance(fill.fill_time, datetime) else (datetime.fromisoformat(fill.fill_time) if isinstance(fill.fill_time, str) else datetime.utcnow()),
            trade_id=self.current_position.id if hasattr(self.current_position, 'id') else None
        )
        
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
            # Rate > 0: Long Pays (Cost), Short Receives (Rebate)
            # Rate < 0: Short Pays (Cost), Long Receives (Rebate)
            
            actual_cost = Decimal("0")
            
            if self.current_position.direction == TradeDirection.LONG:
                if self.config.funding_rate_daily > 0:
                    actual_cost = funding_fee
                else:
                    actual_cost = -abs(funding_fee)
            else: # SHORT
                if self.config.funding_rate_daily > 0:
                    actual_cost = -funding_fee
                else:
                    actual_cost = abs(funding_fee)

            self.equity -= actual_cost
            if hasattr(self.current_position, 'accumulated_funding'):
                self.current_position.accumulated_funding += actual_cost
            
            if actual_cost > 0:
                logger.debug(f"Funding Fee Paid: {actual_cost:.2f}")
            else:
                logger.debug(f"Funding Fee Received: {abs(actual_cost):.2f}")

    def _update_margin(self, signal: Dict, timestamp: Any) -> None:
        """Update isolated margin for current position."""
        if not self.current_position:
            return
            
        amount = Decimal(str(signal.get("amount", "0")))
        if amount == 0:
            return
            
        # Check if adding or removing
        if amount > 0:
            # Adding margin: check if enough equity
            if self.equity < amount:
                logger.warning(f"Insufficient equity to add margin: {self.equity} < {amount}")
                return
            
            self.equity -= amount
            self.current_position.isolated_margin += amount
            action = "ADDED"
        else:
            # Removing margin: careful check
            # For backtest, we allow removal if remaining margin >= initial required margin
            # (or simply if it doesn't cause immediate liquidation)
            # Conservative rule: must have at least initial margin
            
            abs_amount = abs(amount)
            if self.current_position.isolated_margin < abs_amount:
                logger.warning(f"Insufficient isolated margin to remove: {self.current_position.isolated_margin} < {abs_amount}")
                return
                
            self.equity += abs_amount
            self.current_position.isolated_margin -= abs_amount
            action = "REMOVED"
            
        # Log and Emit event
        logger.info(f"MARGIN {action}: {abs(amount)} | New Isolated Margin: {self.current_position.isolated_margin}")
        
        if self.current_position.metadata is None:
            self.current_position.metadata = {}
        self.current_position.metadata["current_margin"] = float(self.current_position.isolated_margin)
        
        self._emit_event(
            event_type=BacktestEventType.MARGIN_UPDATED,
            details={
                "action": action,
                "amount": float(abs(amount)),
                "new_margin": float(self.current_position.isolated_margin),
                "reason": signal.get("metadata", {}).get("reason", "Manual Update") if isinstance(signal.get("metadata"), dict) else (signal.get("metadata") or "Manual Update")
            },
            timestamp=timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            trade_id=self.current_position.id
        )
        
        # ALSO update levels if provided in the same signal
        if "stop_loss" in signal:
            self.current_position.stop_loss = Decimal(str(signal["stop_loss"]))
            logger.info(f"SL updated during margin update to {self.current_position.stop_loss}")
            
        if "take_profit" in signal:
            self.current_position.take_profit = Decimal(str(signal["take_profit"]))
            logger.info(f"TP updated during margin update to {self.current_position.take_profit}")

    def _check_liquidation(self, candle_high: Decimal, candle_low: Decimal) -> Optional[tuple]:
        """Check if position is liquidated based on leverage and margin."""
        if not self.current_position:
            return None
            
        pos = self.current_position
        # Maintenance Margin Rate (0.5%)
        maintenance_rate = Decimal("0.005")
        
        # Calculate Liquidation Price based on Isolated Margin
        # Long Pliq = Pentry * (1 + MMR) - Misc / Q
        # Short Pliq = Pentry * (1 - MMR) + Misc / Q
        
        # We also need to consider the initial margin from equity if isolated_margin is not set?
        # But we initialized it in _open methods.
        
        if pos.direction == TradeDirection.LONG:
            # P_liq = P_entry * (1 + MMR) - M_iso / Q
            liq_price = pos.avg_entry_price * (Decimal("1") + maintenance_rate) - (pos.isolated_margin / pos.quantity)
            pos.liquidation_price = max(Decimal("0"), liq_price)
            if candle_low <= pos.liquidation_price:
                return (pos.liquidation_price, "LIQUIDATION")
                
        else: # SHORT
            # P_liq = P_entry * (1 - MMR) + M_iso / Q
            liq_price = pos.avg_entry_price * (Decimal("1") - maintenance_rate) + (pos.isolated_margin / pos.quantity)
            pos.liquidation_price = liq_price
            if candle_high >= pos.liquidation_price:
                return (pos.liquidation_price, "LIQUIDATION")
                
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
            
            # Use configured limit fill policy
            is_cross = self.config.limit_fill_policy in ("cross", "cross_volume")
            
            # Determine which can trigger
            if is_cross and candle_open:
                # Cross: Require price to move THROUGH the level or gap past it
                sl_triggered = stop_loss and ((candle_open > stop_loss and candle_low < stop_loss) or (candle_open < stop_loss))
                trailing_triggered = trailing_stop and ((candle_open > trailing_stop and candle_low < trailing_stop) or (candle_open < trailing_stop))
                tp_triggered = take_profit and ((candle_open < take_profit and candle_high > take_profit) or (candle_open > take_profit))
            else:
                # Touch: (Standard/Default)
                # SL/TP Checks (LONG)
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
            
            # Use configured limit fill policy
            is_cross = self.config.limit_fill_policy in ("cross", "cross_volume")
            
            # Determine which can trigger
            if is_cross and candle_open:
                # Cross: Require price to move THROUGH the level or gap past it
                sl_triggered = stop_loss and ((candle_open < stop_loss and candle_high > stop_loss) or (candle_open > stop_loss))
                trailing_triggered = trailing_stop and ((candle_open < trailing_stop and candle_high > trailing_stop) or (candle_open > trailing_stop))
                tp_triggered = take_profit and ((candle_open > take_profit and candle_low < take_profit) or (candle_open < take_profit))
            else:
                # Touch: (Standard/Default)
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
        if self.config.position_sizing == PositionSizing.FIXED_SIZE:
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
        
        # Convert to float for curve storage and performance
        total_equity_flt = float(total_equity)
        peak_equity_flt = float(self.peak_equity)
        initial_capital_flt = float(self.config.initial_capital)
        current_price_flt = float(current_price)
        
        # Calculate drawdown (Float math)
        drawdown_amount_flt = total_equity_flt - peak_equity_flt
        drawdown_percent_flt = (drawdown_amount_flt / peak_equity_flt * 100.0) if peak_equity_flt > 0 else 0.0
        
        # Calculate return (Float math)
        return_percent_flt = ((total_equity_flt - initial_capital_flt) / initial_capital_flt * 100.0)
        
        # Calculate positions value (Float math)
        positions_value_flt = 0.0
        if self.current_position:
            positions_value_flt = float(self.current_position.quantity) * current_price_flt
        
        point = EquityCurvePoint(
            timestamp=timestamp,
            equity=total_equity_flt,
            cash=float(self.equity),  # Current cash balance
            positions_value=positions_value_flt,  # Value of open positions
            drawdown=drawdown_amount_flt,  # Drawdown amount
            drawdown_percent=drawdown_percent_flt,
            return_percent=return_percent_flt,
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
