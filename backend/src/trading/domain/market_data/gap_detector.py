from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from src.trading.domain.market_data import Candle, CandleInterval

@dataclass
class TimeRange:
    start: datetime
    end: datetime

class GapDetector:
    """Domain service for detecting gaps in market data sequences."""
    
    @staticmethod
    def interval_to_timedelta(interval: CandleInterval) -> timedelta:
        """Convert CandleInterval to timedelta."""
        mapping = {
            CandleInterval.ONE_MINUTE: timedelta(minutes=1),
            CandleInterval.THREE_MINUTE: timedelta(minutes=3),
            CandleInterval.FIVE_MINUTE: timedelta(minutes=5),
            CandleInterval.FIFTEEN_MINUTE: timedelta(minutes=15),
            CandleInterval.THIRTY_MINUTE: timedelta(minutes=30),
            CandleInterval.ONE_HOUR: timedelta(hours=1),
            CandleInterval.TWO_HOUR: timedelta(hours=2),
            CandleInterval.FOUR_HOUR: timedelta(hours=4),
            CandleInterval.SIX_HOUR: timedelta(hours=6),
            CandleInterval.EIGHT_HOUR: timedelta(hours=8),
            CandleInterval.TWELVE_HOUR: timedelta(hours=12),
            CandleInterval.ONE_DAY: timedelta(days=1),
            CandleInterval.THREE_DAY: timedelta(days=3),
            CandleInterval.ONE_WEEK: timedelta(weeks=1),
            CandleInterval.ONE_MONTH: timedelta(days=30), # Approximation
        }
        return mapping.get(interval, timedelta(minutes=1))

    @classmethod
    def detect_gaps(
        cls,
        candles: List[Candle],
        start_time: datetime,
        end_time: datetime,
        interval: CandleInterval
    ) -> List[TimeRange]:
        """
        Identify missing time ranges in a sequence of candles.
        
        Args:
            candles: List of existing candles (must be sorted by open_time)
            start_time: Expected start of Data
            end_time: Expected end of Data
            interval: Data timeframe
            
        Returns:
            List of TimeRange representing gaps
        """
        print(f"DEBUG: GapDetector.detect_gaps called with {len(candles)} candles. Start={start_time}, End={end_time}")
        delta = cls.interval_to_timedelta(interval)
        gaps: List[TimeRange] = []
        
        # Ensure timezone awareness compatibility
        if start_time.tzinfo is None and end_time.tzinfo is not None:
             start_time = start_time.replace(tzinfo=end_time.tzinfo)
        
        current_expected = start_time
        
        # If no candles, the entire range is a gap
        if not candles:
            return [TimeRange(start=start_time, end=end_time)]

        for candle in candles:
            # Check for gap before this candle
            candle_start = candle.open_time
            
            # If candle starts after expected time, we have a gap
            if candle_start > current_expected:
                # The gap ends effectively at the candle start
                # (or just before it). We'll mark the range.
                gaps.append(TimeRange(start=current_expected, end=candle_start))
            
            # Move expected to next slot
            current_expected = candle_start + delta

        # Check for gap after last candle until end_time
        if current_expected < end_time:
             gaps.append(TimeRange(start=current_expected, end=end_time))
             
        return gaps
