# data/mock_data.py

def get_watchlist_symbols():
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


def get_mock_prices():
    return {
        "BTCUSDT": 62000.5,
        "ETHUSDT": 3100.25,
        "BNBUSDT": 415.75,
        "SOLUSDT": 145.3,
    }


def get_mock_orderbook():
    return [
        ("BID", 62000.5, 1.2),
        ("ASK", 62001.2, 0.8),
        ("BID", 61999.8, 2.5),
        ("ASK", 62002.0, 1.1),
    ]

def get_mock_positions():
    return [
        ("BTCUSDT", "LONG", 61000, 62000, 0.5, 500, 60000, 63000),
        ("ETHUSDT", "SHORT", 3000, 2950, 1.0, 50, 3100, 2800),
    ]

def get_mock_trades():
    return [
        ("2025-01-01 12:00", "BTCUSDT", "LONG", 61000, 0.5, 200, "Closed"),
        ("2025-01-02 15:30", "ETHUSDT", "SHORT", 3000, 1.0, 20, "Open"),
    ]
