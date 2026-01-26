
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_mtf_strategy():
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres123@localhost:5432/trading_platform")
        cur = conn.cursor()
        
        with open("/home/qwe/Desktop/zxc/mtf_strategy.py", "r") as f:
            code = f.read()
            
        cur.execute(
            "UPDATE strategies SET code_content = %s WHERE name = 'Martingale Smart MTF (Fixed SL)'",
            (code,)
        )
        conn.commit()
        logger.info("Successfully updated Martingale Smart MTF strategy in DB.")
        
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Update failed: {e}")

if __name__ == "__main__":
    update_mtf_strategy()
