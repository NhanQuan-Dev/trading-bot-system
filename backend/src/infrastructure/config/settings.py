# File: /futures-monitor/futures-monitor/src/infrastructure/config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_KEY = os.getenv("API_KEY", "your_default_api_key")
    API_SECRET = os.getenv("API_SECRET", "your_default_api_secret")
    REST_BASE = os.getenv("REST_BASE", "https://demo-fapi.binance.com")
    WS_BASE = os.getenv("WS_BASE", "wss://fstream.binancefuture.com")
    TRACKED_SYMBOLS = os.getenv("TRACKED_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT").split(",")
    ORDERBOOK_SYMBOL = os.getenv("ORDERBOOK_SYMBOL", "BTCUSDT")
    RENDER_INTERVAL = float(os.getenv("RENDER_INTERVAL", 1.0))
    USE_ALT_SCREEN = os.getenv("USE_ALT_SCREEN", "True").lower() in ("true", "1", "t")