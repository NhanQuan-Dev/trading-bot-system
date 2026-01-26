
import psycopg2
import pandas as pd
import pandas_ta as ta

def compare():
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres123@localhost:5432/trading_platform")
        cur = conn.cursor()
        
        # We start from Jan 1st to ensure warmup is perfect
        query = """
            SELECT timestamp AT TIME ZONE 'UTC', close 
            FROM market_prices 
            WHERE symbol = 'BTCUSDT' AND interval = '1m'
            AND timestamp >= '2024-01-01 00:00:00+00'
            AND timestamp <= '2024-01-22 20:59:59+00'
            ORDER BY timestamp ASC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        timestamps = [r[0] for r in rows]
        closes = [float(r[1]) for r in rows]
        
        # --- NEW (Vectorized) ---
        df = pd.DataFrame({"close": closes})
        rsi_new = ta.rsi(df["close"], length=14).tolist()
        high_new = df["close"].rolling(window=20).max().tolist()
        
        # --- OLD (Incremental simulation) ---
        # Note: In the old engine, at each step 'idx', closes had candles 0 to idx.
        # So we just take the values at index 'idx' from the vectorized result
        # because ta.rsi(df[:idx+1]) results in the same value at point 'idx' 
        # as ta.rsi(df) if the history is the same.
        
        print(f"{'Timestamp':<25} | {'RSI':<10} | {'High':<10} | {'Price':<10}")
        print("-" * 65)
        
        for i in range(len(timestamps)):
            ts = timestamps[i]
            ts_str = str(ts)
            
            # Focus on the window Jan 22 19:15 to 19:30 UTC
            if "2024-01-22 19:15" <= ts_str <= "2024-01-22 19:30":
                p = closes[i]
                r = rsi_new[i]
                h = high_new[i]
                
                trigger_rsi = "ENTRY_RSI" if r < 30 else ""
                trigger_high = "ENTRY_HIGH" if p >= h else ""
                
                print(f"{ts_str:<25} | {str(r)[:8]:<10} | {str(h)[:8]:<10} | {p:<10} | {trigger_rsi} {trigger_high}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    compare()
