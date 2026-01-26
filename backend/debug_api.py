
import asyncio
import uuid
import sys
import os
import time
import datetime
import httpx
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import select

# Load environment variables
load_dotenv()

# Ensure backend src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Imports for Database Setup
from src.trading.infrastructure.persistence.database import AsyncSessionLocal
from src.trading.infrastructure.persistence.models import UserModel, StrategyModel, APIConnectionModel
from src.trading.domain.user import HashedPassword
from src.trading.infrastructure.repositories.exchange_repository import ExchangeRepository
from src.trading.domain.exchange import ExchangeConnection, APICredentials, ExchangePermissions, ExchangeType, ConnectionStatus

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "debug_user@example.com"
TEST_PASSWORD = "debug_password123"
TEST_STRATEGY_NAME = "HighFrequencyTest"
TEST_CONN_NAME = "Debug Binance"

async def setup_environment():
    """
    Ensures the test user, strategy, and exchange connection exist in the database.
    This replaces the functionality of create_repro_user.py.
    """
    print("--- Setting up Environment ---")
    async with AsyncSessionLocal() as session:
        # 1. Ensure User Exists
        res = await session.execute(select(UserModel).where(UserModel.email == TEST_EMAIL))
        user_model = res.scalar_one_or_none()
        
        hashed_pwd_obj = HashedPassword.from_plain(TEST_PASSWORD)
        hashed_pwd_str = hashed_pwd_obj.value

        if user_model:
            print(f"User {TEST_EMAIL} exists. Updating password...")
            user_model.password_hash = hashed_pwd_str
            user_model.is_active = True
        else:
            print(f"Creating new user {TEST_EMAIL}...")
            user_model = UserModel(
                id=uuid.uuid4(),
                email=TEST_EMAIL,
                password_hash=hashed_pwd_str,
                is_active=True,
                full_name="Debug User"
            )
            session.add(user_model)
            
        await session.commit()
        
        # 2. Clean and Create Strategy
        # Delete existing strategies to avoid confusion
        from sqlalchemy import delete
        await session.execute(delete(StrategyModel).where(StrategyModel.user_id == user_model.id))
        await session.commit()
        
        print(f"Creating strategy '{TEST_STRATEGY_NAME}'...")
        strategy = StrategyModel(
            id=uuid.uuid4(),
            user_id=user_model.id,
            name=TEST_STRATEGY_NAME,
            strategy_type="CUSTOM",
            description="Strategy for API Debugging",
            is_active=True,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
            parameters={"param": 1},
            code_content=None
        )
        session.add(strategy)
        await session.commit()
        strategy_id = str(strategy.id)

        # 3. Ensure Exchange Connection Exists
        repo = ExchangeRepository(session)
        conns = await repo.find_by_user_and_exchange(user_model.id, ExchangeType.BINANCE)
        
        existing_conn = None
        for c in conns:
            if c.name == TEST_CONN_NAME:
                existing_conn = c
                break
        
        if not existing_conn:
            print(f"Creating exchange connection '{TEST_CONN_NAME}'...")
            new_conn = ExchangeConnection(
                id=uuid.uuid4(),
                user_id=user_model.id,
                exchange_type=ExchangeType.BINANCE,
                name=TEST_CONN_NAME,
                credentials=APICredentials(
                    api_key="test_key",
                    secret_key="test_secret"
                ),
                permissions=ExchangePermissions(read_only=True),
                is_testnet=True,
                status=ConnectionStatus.CONNECTED,
                created_at=datetime.datetime.utcnow()
            )
            await repo.save(new_conn)
            await session.commit()
            connection_id = str(new_conn.id)
            print(f"Created connection {connection_id}")
        else:
            print(f"Exchange connection '{TEST_CONN_NAME}' exists.")
            connection_id = str(existing_conn.id)
            
        print("Environment Setup Complete.\n")
        return {"strategy_id": strategy_id, "connection_id": connection_id}

async def run_api_tests(context=None):
    """
    Runs API tests using the setup environment.
    """
    print("--- Running API Tests ---")
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        # 1. Login
        print(f"Logging in as {TEST_EMAIL}...")
        try:
            resp = await client.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            resp.raise_for_status()
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("Login successful.")
        except Exception as e:
            print(f"Login failed: {e}")
            if 'resp' in locals():
                print(resp.text)
            return

        # 2. Get IDs from context or fetch
        strategy_id = context.get("strategy_id") if context else None
        connection_id = context.get("connection_id") if context else None

        if not strategy_id:
            print("Fetching strategies...")
            resp = await client.get(f"{BASE_URL}/strategies", headers=headers)
            strategies = resp.json()
            for s in strategies:
                if s["name"] == TEST_STRATEGY_NAME:
                    strategy_id = s["id"]
                    break
            if not strategy_id:
                print(f"Strategy '{TEST_STRATEGY_NAME}' not found via API.")
                print(f"Available: {[s['name'] for s in strategies]}")
                return

        if not connection_id:
            print("Fetching exchange connections...")
            resp = await client.get(f"{BASE_URL}/exchanges/connections", headers=headers)
            connections = resp.json()
            for c in connections:
                if c["name"] == TEST_CONN_NAME:
                    connection_id = c["id"]
                    break
            if not connection_id and connections:
                 connection_id = connections[0]["id"]
            if not connection_id:
                 print("No connection found.")
                 return

        print(f"Using Strategy ID: {strategy_id}")
        print(f"Using Connection ID: {connection_id}")

        # 4. Run Backtest Test
        payload = {
            "strategy_id": strategy_id,
            "exchange_connection_id": connection_id,
            "config": {
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-02-01T00:00:00",
                "initial_capital": 10000,
                "leverage": 1,
                "slippage_model": "fixed",
                "slippage_percent": 0.001,
                "commission_model": "fixed_rate",
                "commission_percent": 0.001
            }
        }
        
        print("\nCreating Backtest 1...")
        start_time = time.time()
        try:
            resp = await client.post(
                f"{BASE_URL}/backtests", 
                json=payload, 
                headers=headers
            )
            print(f"Backtest 1 Status: {resp.status_code} (Time: {time.time() - start_time:.2f}s)")
            if resp.status_code not in [200, 201, 202]:
                print(f"Error: {resp.text}")
            else:
                print(f"Backtest 1 ID: {resp.json().get('id')}")
        except Exception as e:
            print(f"Request Error: {e}")

        # 5. Run Concurrent Test (Immediate Second Request)
        print("\nCreating Backtest 2 (Immediate Concurrent Request)...")
        start_time = time.time()
        try:
            resp = await client.post(
                f"{BASE_URL}/backtests", 
                json=payload, 
                headers=headers
            )
            print(f"Backtest 2 Status: {resp.status_code} (Time: {time.time() - start_time:.2f}s)")
            if resp.status_code not in [200, 201, 202]:
                print(f"Error: {resp.text}")
            else:
                 print(f"Backtest 2 ID: {resp.json().get('id')}")
        except Exception as e:
            print(f"Request Error: {e}")

        print("\nAPI Tests Complete.")

async def main():
    context = await setup_environment()
    await run_api_tests(context)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup-only":
        asyncio.run(setup_environment())
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        asyncio.run(run_api_tests())
    else:
        asyncio.run(main())
