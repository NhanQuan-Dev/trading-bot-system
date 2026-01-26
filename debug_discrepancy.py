
import psycopg2
import pandas as pd
import pandas_ta as ta
from decimal import Decimal

class MockPosition:
    def __init__(self, entry_price):
        self.avg_entry_price = float(entry_price)

def debug_discrepancy():
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres123@localhost:5432/trading_platform")
        cur = conn.cursor()
        
        query = """
            SELECT timestamp AT TIME ZONE 'UTC', open, high, low, close 
            FROM market_prices 
            WHERE symbol = 'BTCUSDT' AND interval = '1m'
            AND timestamp >= '2024-01-22 18:30:00+00'
            AND timestamp <= '2024-01-22 20:30:00+00'
            ORDER BY timestamp ASC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        candles = []
        for r in rows:
            candles.append({
                "timestamp": r[0],
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4])
            })
            
        print(f"Fetched {len(candles)} candles.")
        
        # INDICATORS
        rsi_period = 14
        breakout_period = 20
        df = pd.DataFrame(candles)
        rsi_new = ta.rsi(df["close"], length=rsi_period).tolist()
        high_new = df["close"].rolling(window=breakout_period).max().tolist()
        
        # --- SIMULATION ---
        # We know Trade 2 exited at 02:16. So we start fresh after that.
        
            print(f"{'Timestamp':<25} | {'Old RSI':<10} | {'New RSI':<10} | {'Old High':<10} | {'New High':<10} | {'Price':<10}")
            for i in range(len(candles)):
                ts = candles[i]["timestamp"]
                p = candles[i]["close"]
                ro = rsi_vals[i]
                rn = rsi_vals_new[i]
                ho = high_vals[i]
                hn = high_vals_new[i]
                
                ts_str = str(ts)
                if "19:15" <= ts_str[11:] <= "19:30":
                    print(f"{ts_str:<25} | {str(ro)[:8]:<10} | {str(rn)[:8]:<10} | {str(ho)[:8]:<10} | {str(hn)[:8]:<10} | {p:<10}")

        # SIMULATION CALL
        df = pd.DataFrame(candles)
        rsi_new = ta.rsi(df["close"], length=rsi_period).tolist()
        high_new = df["close"].rolling(window=breakout_period).max().tolist()
        
        rsi_old = []
        high_old = []
        closes = []
        for c in candles:
            closes.append(c["close"])
            if len(closes) < 20:
                rsi_old.append(None); high_old.append(None)
                continue
            rsi_old.append(ta.rsi(pd.Series(closes), length=14).iloc[-1])
            high_old.append(max(closes[-20:]))

        print_comparison(rsi_old, rsi_new, high_old, high_new)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_discrepancy()
