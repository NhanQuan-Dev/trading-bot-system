"""Timeframe utilities for multi-timeframe backtesting."""

from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class MultiTimeframeContext:
    """
    Context object injected into multi-timeframe strategies.
    
    Attributes:
        current_candles: Dictionary mapping timeframe (e.g., '1h') to the latest COMPLETED candle (dict).
                         This prevents look-ahead bias (using current developing candle).
                         Key: Timeframe string (e.g. '1h')
                         Value: Candle dict
        history: Dictionary mapping timeframe to a list of recent candles.
                 Key: Timeframe string
                 Value: List of candle dicts
    """
    current_candles: Dict[str, Dict[str, Any]]
    history: Dict[str, List[Dict[str, Any]]]


TIMEFRAME_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def resample_candles_to_htf(
    candles_1m: List[Dict],
    target_timeframe: str,
) -> List[Dict]:
    """
    Resample 1-minute candles to higher timeframe.
    
    Args:
        candles_1m: List of 1m OHLCV candles
        target_timeframe: Target timeframe (e.g., "1h", "4h", "1d")
    
    Returns:
        List of aggregated OHLCV candles at target timeframe
    """
    if target_timeframe == "1m":
        return candles_1m
    
    if target_timeframe not in TIMEFRAME_MINUTES:
        raise ValueError(f"Unsupported timeframe: {target_timeframe}")
    
    interval_minutes = TIMEFRAME_MINUTES[target_timeframe]
    htf_candles = []
    
    # Group candles by timeframe windows
    current_window = []
    window_start_time = None
    
    for candle in candles_1m:
        timestamp = candle["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Determine window start for this candle
        # Floor to nearest interval boundary
        minutes_since_epoch = int(timestamp.timestamp() / 60)
        window_minutes = (minutes_since_epoch // interval_minutes) * interval_minutes
        candle_window_start = datetime.fromtimestamp(window_minutes * 60, tz=timezone.utc)
        
        # Start new window if needed
        if window_start_time is None:
            window_start_time = candle_window_start
            current_window = [candle]
        elif candle_window_start != window_start_time:
            # Finish current window and start new one
            if current_window:
                htf_candles.append(_aggregate_candles(current_window, window_start_time))
            window_start_time = candle_window_start
            current_window = [candle]
        else:
            # Add to current window
            current_window.append(candle)
    
    # Don't forget last window
    if current_window:
        htf_candles.append(_aggregate_candles(current_window, window_start_time))
    
    return htf_candles


def _aggregate_candles(candles: List[Dict], window_start: datetime) -> Dict:
    """Aggregate multiple candles into one OHLCV candle."""
    if not candles:
        raise ValueError("Cannot aggregate empty candle list")
    
    # OHLC aggregation (Optimized: Use float directly since output is float)
    # This avoids ~1.5 million unnecessary Decimal conversions for a 1-year backtest
    open_price = float(candles[0]["open"])
    high_price = max(float(c["high"]) for c in candles)
    low_price = min(float(c["low"]) for c in candles)
    close_price = float(candles[-1]["close"])
    volume = sum(float(c.get("volume", 0)) for c in candles)
    
    return {
        "timestamp": window_start,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }


def get_candles_in_htf_window(
    candles_1m: List[Dict],
    htf_candle_timestamp: datetime,
    htf_timeframe: str,
) -> List[Dict]:
    """
    Get all 1m candles that belong to a specific HTF candle window.
    
    Args:
        candles_1m: Full list of 1m candles
        htf_candle_timestamp: Start timestamp of HTF candle
        htf_timeframe: HTF timeframe string
    
    Returns:
        List of 1m candles within that HTF window
    """
    interval_minutes = TIMEFRAME_MINUTES[htf_timeframe]
    window_end = htf_candle_timestamp + timedelta(minutes=interval_minutes)
    
    matching_candles = []
    for candle in candles_1m:
        timestamp = candle["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        if htf_candle_timestamp <= timestamp < window_end:
            matching_candles.append(candle)
    
    return matching_candles


def get_next_htf_window_candles(
    candles_1m: List[Dict],
    htf_candle_timestamp: datetime,
    htf_timeframe: str,
) -> List[Dict]:
    """
    Get 1m candles from the NEXT HTF window (after signal is generated).
    
    Per backtestspec3.md:
    - HTF 09:00 candle closes at 10:00
    - Signal generated at 10:00
    - Execution must use 1m candles from 10:00-10:59 (next window)
    
    This prevents look-ahead bias by ensuring we don't execute
    within the same window used to generate the signal.
    
    Args:
        candles_1m: Full list of 1m candles
        htf_candle_timestamp: Start timestamp of HTF candle that closed
        htf_timeframe: HTF timeframe string
    
    Returns:
        List of 1m candles from the NEXT HTF window
    """
    interval_minutes = TIMEFRAME_MINUTES[htf_timeframe]
    
    # Next window starts when current HTF candle closes
    next_window_start = htf_candle_timestamp + timedelta(minutes=interval_minutes)
    next_window_end = next_window_start + timedelta(minutes=interval_minutes)
    
    matching_candles = []
    for candle in candles_1m:
        timestamp = candle["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        if next_window_start <= timestamp < next_window_end:
            matching_candles.append(candle)
    
    return matching_candles
