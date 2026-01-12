import os
import sys
from sqlalchemy import create_engine, text

# Add backend to path (though not strictly needed if we just use SQL)
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Hardcode fallback or try to read env?
# Best to verify .env
env_path = os.path.join(os.getcwd(), 'backend', '.env')
db_url = None

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                db_url = line.strip().split('=', 1)[1]
                break

if not db_url:
    print("Could not find DATABASE_URL in backend/.env")
    # Fallback to default commonly used
    db_url = "postgresql+asyncpg://postgres:password@localhost:5432/trading_platform"

# Convert asyncpg to psycopg2 for sync execution
if "+asyncpg" in db_url:
    sync_url = db_url.replace("+asyncpg", "+psycopg2")
else:
    sync_url = db_url

print(f"Connecting to: {sync_url}")

engine = create_engine(sync_url)

def run_migration():
    try:
        with engine.connect() as conn:
            print("Checking if column 'code_content' exists in 'strategies' table...")
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='strategies' AND column_name='code_content';")
            result = conn.execute(check_sql).fetchone()
            
            if result:
                print("Column 'code_content' already exists. Skipping.")
            else:
                print("Adding column 'code_content'...")
                sql = text("ALTER TABLE strategies ADD COLUMN code_content TEXT;")
                conn.execute(sql)
                conn.commit()
                print("Migration successful: Added 'code_content' to 'strategies'.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
