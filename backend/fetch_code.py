
import psycopg2
import sys

def get_strategy_code(name):
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres123@localhost:5432/trading_platform")
        cur = conn.cursor()
        cur.execute("SELECT code_content FROM strategies WHERE id = %s", ('715cb977-01a5-49d9-bd09-8669e85d311c',))
        row = cur.fetchone()
        if row:
            with open("fetched_strategy.py", "w") as f:
                f.write(row[0])
            print("Successfully wrote code to fetched_strategy.py")
        else:
            print("Strategy not found")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_strategy_code("dummy")
