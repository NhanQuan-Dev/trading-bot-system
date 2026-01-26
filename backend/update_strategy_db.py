
import psycopg2
import sys
import os

def update_strategy_code(strategy_id, file_path):
    try:
        # Read the new code content
        with open(file_path, 'r') as f:
            new_code = f.read()
            
        print(f"Read {len(new_code)} bytes from {file_path}")
        
        conn = psycopg2.connect("postgresql://postgres:postgres123@localhost:5432/trading_platform")
        cur = conn.cursor()
        
        # Verify it exists first
        cur.execute("SELECT name FROM strategies WHERE id = %s", (strategy_id,))
        row = cur.fetchone()
        if not row:
            print(f"Strategy {strategy_id} not found!")
            return
            
        print(f"Updating Strategy: {row[0]}")
        
        # Update code_content
        cur.execute(
            "UPDATE strategies SET code_content = %s, updated_at = NOW() WHERE id = %s",
            (new_code, strategy_id)
        )
        
        conn.commit()
        print("Update committed successfully.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()

if __name__ == "__main__":
    STRATEGY_ID = '715cb977-01a5-49d9-bd09-8669e85d311c'
    FILE_PATH = 'backend/fixed_strategy.py'
    
    update_strategy_code(STRATEGY_ID, FILE_PATH)
