# Sample data for testing purposes

sample_account_data = {
    "total_wallet_balance": "1000.00",
    "available_balance": "500.00",
    "assets": [
        {"asset": "USDT", "walletBalance": "1000.00", "crossWalletBalance": "500.00"},
        {"asset": "BTC", "walletBalance": "0.0", "crossWalletBalance": "0.0"},
    ],
    "positions": [
        {
            "symbol": "BTCUSDT",
            "positionAmt": "0.1",
            "entryPrice": "50000.00",
            "leverage": "10",
            "unrealizedProfit": "500.00",
            "marginType": "isolated",
            "positionSide": "LONG",
        },
        {
            "symbol": "ETHUSDT",
            "positionAmt": "-1.0",
            "entryPrice": "2000.00",
            "leverage": "5",
            "unrealizedProfit": "-100.00",
            "marginType": "cross",
            "positionSide": "SHORT",
        },
    ],
}

sample_market_data = {
    "mark_prices": {
        "BTCUSDT": "55000.00",
        "ETHUSDT": "2100.00",
        "BNBUSDT": "300.00",
        "SOLUSDT": "150.00",
    },
}

sample_orderbook_data = {
    "bids": [
        ("54900.00", "0.5"),
        ("54800.00", "1.0"),
        ("54700.00", "2.0"),
    ],
    "asks": [
        ("55000.00", "0.5"),
        ("55100.00", "1.0"),
        ("55200.00", "2.0"),
    ],
}