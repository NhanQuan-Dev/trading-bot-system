# Binance USDⓈ-Margined Futures — API Catalogue (Integration Prep)

## Overview
- Base REST: `https://fapi.binance.com`  
- Testnet REST: `https://demo-fapi.binance.com`  
- Base WebSocket Market: `wss://fstream.binance.com`  
- Testnet WebSocket Market: `wss://fstream.binancefuture.com`
- Returns JSON; timestamps are in milliseconds; data ascending (oldest→newest).
- Security types: `TRADE`, `USER_DATA` are `SIGNED`; API key in `X-MBX-APIKEY`.
- Rate limits and error handling per General Info.

Source: General Info (developers.binance.com/docs/derivatives/usds-margined-futures/general-info)

---

## Error Handling & Rate Limits
- HTTP 4XX: client issues; 429: rate limit; 418: auto-ban after continued 429; 5XX: server errors.  
- 503 message variants:  
  - Unknown error… execution status unknown → verify via WS or order query; prefer single orders during peaks.  
  - Service Unavailable → failure; retry with backoff.  
  - -1008 throttled → failure; retry/backoff; reduce concurrency; reduce-only/close-position exempt.  
- Order rate and request weights exposed via `GET /fapi/v1/exchangeInfo`.

Source: General Info (developers.binance.com/docs/derivatives/usds-margined-futures/general-info)

---

## REST — Market Data

### Exchange Information
- Category: Market Data  
- Endpoint: `GET /fapi/v1/exchangeInfo`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information  
- Description: Exchange-wide filters, assets, symbols, rateLimits, order types, timeInForce.  
- Parameters: none typical; see doc.  
- Response: includes `assets[]`, `symbols[]` and `rateLimits[]` with filters such as `PRICE_FILTER`, `LOT_SIZE`, `MARKET_LOT_SIZE`, `PERCENT_PRICE`, `MIN_NOTIONAL`, `MAX_NUM_ORDERS`, `MAX_NUM_ALGO_ORDERS`.  
- Response example:

```json
{
  "exchangeFilters": [],
  "rateLimits": [
    {"interval": "MINUTE", "intervalNum": 1, "limit": 2400, "rateLimitType": "REQUEST_WEIGHT"},
    {"interval": "MINUTE", "intervalNum": 1, "limit": 1200, "rateLimitType": "ORDERS"}
  ],
  "serverTime": 1565613908500,
  "assets": [
    {"asset": "BTC", "marginAvailable": true, "autoAssetExchange": "-0.10"},
    {"asset": "USDT", "marginAvailable": true, "autoAssetExchange": "0"}
  ],
  "symbols": [
    {
      "symbol": "BLZUSDT",
      "pair": "BLZUSDT",
      "contractType": "PERPETUAL",
      "deliveryDate": 4133404800000,
      "onboardDate": 1598252400000,
      "status": "TRADING",
      "baseAsset": "BLZ",
      "quoteAsset": "USDT",
      "marginAsset": "USDT",
      "pricePrecision": 5,
      "quantityPrecision": 0,
      "filters": [
        {"filterType": "PRICE_FILTER", "maxPrice": "300", "minPrice": "0.0001", "tickSize": "0.0001"},
        {"filterType": "LOT_SIZE", "maxQty": "10000000", "minQty": "1", "stepSize": "1"},
        {"filterType": "MARKET_LOT_SIZE", "maxQty": "590119", "minQty": "1", "stepSize": "1"},
        {"filterType": "MAX_NUM_ORDERS", "limit": 200},
        {"filterType": "MAX_NUM_ALGO_ORDERS", "limit": 10},
        {"filterType": "MIN_NOTIONAL", "notional": "5.0"},
        {"filterType": "PERCENT_PRICE", "multiplierUp": "1.1500", "multiplierDown": "0.8500", "multiplierDecimal": "4"}
      ],
      "OrderType": [
        "LIMIT",
        "MARKET",
        "STOP",
        "STOP_MARKET",
        "TAKE_PROFIT",
        "TAKE_PROFIT_MARKET",
        "TRAILING_STOP_MARKET"
      ],
      "timeInForce": ["GTC", "IOC", "FOK", "GTX"],
      "liquidationFee": "0.010000",
      "marketTakeBound": "0.30"
    }
  ],
  "timezone": "UTC"
}
```

### Kline Candlestick Data
- Category: Market Data  
- Endpoint: `GET /fapi/v1/klines`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data  
- Description: Symbol klines; unique by open time.  
- Parameters: `symbol`, `interval`, optional `startTime`, `endTime`, `limit`.  
- Response example:

```json
[
  [
    1499040000000,
    "0.01634790",
    "0.80000000",
    "0.01575800",
    "0.01577100",
    "148976.11427815",
    1499644799999,
    "2434.19055334",
    308,
    "1756.87402397",
    "28.46694368",
    "17928899.62484339"
  ]
]
```

### Continuous Contract Klines
- Category: Market Data  
- Endpoint: `GET /fapi/v1/continuousKlines`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Continuous-Contract-Kline-Candlestick-Data  
- Description: Klines by contract type (`PERPETUAL`, `CURRENT_QUARTER`, `NEXT_QUARTER`).  
- Parameters: `pair`, `contractType`, `interval`, optional time window and `limit`.  
- Response example:

```json
[
  [
    1607444700000,
    "18879.99",
    "18900.00",
    "18878.98",
    "18896.13",
    "492.363",
    1607444759999,
    "9302145.66080",
    1874,
    "385.983",
    "7292402.33267",
    "0"
  ]
]
```

### Index Price Klines
- Category: Market Data  
- Endpoint: `GET /fapi/v1/indexPriceKlines`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Index-Price-Kline-Candlestick-Data  
- Description: Index price klines for a pair.  
- Parameters: `pair`, `interval`, optional time window and `limit`.  
- Response example:

```json
[
  [
    1591256400000,
    "9653.69440000",
    "9653.69640000",
    "9651.38600000",
    "9651.55200000",
    "0",
    1591256459999,
    "0",
    60,
    "0",
    "0",
    "0"
  ]
]
```

### Mark Price Klines
- Category: Market Data  
- Endpoint: `GET /fapi/v1/markPriceKlines`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data  
- Description: Mark price klines for a symbol.  
- Parameters: `symbol`, `interval`, optional time window and `limit`.  
- Response example:

```json
[
  [
    1591256460000,
    "9653.29201333",
    "9654.56401333",
    "9653.07367333",
    "9653.07367333",
    "0",
    1591256519999,
    "0",
    60,
    "0",
    "0",
    "0"
  ]
]
```

### Funding Rate History
- Category: Market Data  
- Endpoint: `GET /fapi/v1/fundingRate`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History  
- Description: Historical funding rates; shares IP rate limit with `GET /fapi/v1/fundingInfo`.  
- Parameters: typical `symbol`, optional `startTime`, `endTime`, `limit`.  
- Response example:

```json
[
  {"symbol": "BTCUSDT", "fundingRate": "-0.03750000", "fundingTime": 1570608000000, "markPrice": "34287.54619963"},
  {"symbol": "BTCUSDT", "fundingRate": "0.00010000", "fundingTime": 1570636800000, "markPrice": "34287.54619963"}
]
```

### Old Trades Lookup
- Category: Market Data  
- Endpoint: `GET /fapi/v1/historicalTrades`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Old-Trades-Lookup  
- Description: Older market trades (last 3 months). Excludes insurance/ADL trades.  
- Parameters: `symbol`, optional `limit` (max 500), `fromId`.  
- Response example:

```json
[
  {
    "id": 28457,
    "price": "4.00000100",
    "qty": "12.00000000",
    "quoteQty": "8000.00",
    "time": 1499865549590,
    "isBuyerMaker": true,
    "isRPITrade": true
  }
]
```

---

## REST — Trade (Orders)

### New Order
- Category: Trade  
- Endpoint: `POST /fapi/v1/order`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api  
- Description: Place an order. Supports `LIMIT`, `MARKET`, `STOP`, `STOP_MARKET`, `TAKE_PROFIT`, `TAKE_PROFIT_MARKET`, `TRAILING_STOP_MARKET`, `GTD`.  
- Parameters: `symbol`, `side`, `type`, conditional `timeInForce/quantity/price/stopPrice/callbackRate`, `positionSide`, `reduceOnly`, `closePosition`, `activationPrice`, `workingType`, `priceProtect`, `newOrderRespType`, `priceMatch`, `selfTradePreventionMode`, `goodTillDate`, `recvWindow`, `timestamp`.  
- Response example:

```json
{
  "clientOrderId": "testOrder",
  "cumQty": "0",
  "cumQuote": "0",
  "executedQty": "0",
  "orderId": 22542179,
  "avgPrice": "0.00000",
  "origQty": "10",
  "price": "0",
  "reduceOnly": false,
  "side": "BUY",
  "positionSide": "SHORT",
  "status": "NEW",
  "stopPrice": "9300",
  "symbol": "BTCUSDT",
  "timeInForce": "GTC",
  "type": "TRAILING_STOP_MARKET",
  "origType": "TRAILING_STOP_MARKET",
  "activatePrice": "9020",
  "priceRate": "0.3",
  "updateTime": 1566818724722,
  "workingType": "CONTRACT_PRICE",
  "priceProtect": false,
  "priceMatch": "NONE",
  "selfTradePreventionMode": "NONE",
  "goodTillDate": 1693207680000
}
```

### Place Multiple Orders
- Category: Trade  
- Endpoint: `POST /fapi/v1/batchOrders`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Place-Multiple-Orders  
- Description: Submit up to 5 orders concurrently.  
- Parameters: `batchOrders` (list JSON), `recvWindow`, `timestamp`; each order’s fields follow New Order rules.  
- Response example:

```json
[
  {
    "clientOrderId": "testOrder",
    "cumQty": "0",
    "cumQuote": "0",
    "executedQty": "0",
    "orderId": 22542179,
    "avgPrice": "0.00000",
    "origQty": "10",
    "price": "0",
    "reduceOnly": false,
    "side": "BUY",
    "positionSide": "SHORT",
    "status": "NEW",
    "stopPrice": "9300",
    "symbol": "BTCUSDT",
    "timeInForce": "GTC",
    "type": "TRAILING_STOP_MARKET",
    "origType": "TRAILING_STOP_MARKET",
    "activatePrice": "9020",
    "priceRate": "0.3",
    "updateTime": 1566818724722,
    "workingType": "CONTRACT_PRICE",
    "priceProtect": false,
    "priceMatch": "NONE",
    "selfTradePreventionMode": "NONE",
    "goodTillDate": 1693207680000
  },
  {"code": -2022, "msg": "ReduceOnly Order is rejected."}
]
```

### Cancel Order
- Category: Trade  
- Endpoint: `DELETE /fapi/v1/order`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Order  
- Description: Cancel an active order.  
- Parameters: typical `symbol` plus `orderId` or `origClientOrderId`, `recvWindow`, `timestamp`.  
- Response example:

```json
{
  "clientOrderId": "myOrder1",
  "cumQty": "0",
  "cumQuote": "0",
  "executedQty": "0",
  "orderId": 283194212,
  "origQty": "11",
  "origType": "TRAILING_STOP_MARKET",
  "price": "0",
  "reduceOnly": false,
  "side": "BUY",
  "positionSide": "SHORT",
  "status": "CANCELED",
  "stopPrice": "9300",
  "closePosition": false,
  "symbol": "BTCUSDT",
  "timeInForce": "GTC",
  "type": "TRAILING_STOP_MARKET",
  "activatePrice": "9020",
  "priceRate": "0.3",
  "updateTime": 1571110484038,
  "workingType": "CONTRACT_PRICE",
  "priceProtect": false,
  "priceMatch": "NONE",
  "selfTradePreventionMode": "NONE",
  "goodTillDate": 1693207680000
}
```

### Cancel Multiple Orders
- Category: Trade  
- Endpoint: `DELETE /fapi/v1/batchOrders`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Multiple-Orders  
- Description: Cancel multiple orders.  
- Parameters: order identifiers in list, `recvWindow`, `timestamp`.  
- Response example:

```json
[
  {
    "clientOrderId": "myOrder1",
    "cumQty": "0",
    "cumQuote": "0",
    "executedQty": "0",
    "orderId": 283194212,
    "origQty": "11",
    "origType": "TRAILING_STOP_MARKET",
    "price": "0",
    "reduceOnly": false,
    "side": "BUY",
    "positionSide": "SHORT",
    "status": "CANCELED",
    "stopPrice": "9300",
    "closePosition": false,
    "symbol": "BTCUSDT",
    "timeInForce": "GTC",
    "type": "TRAILING_STOP_MARKET",
    "activatePrice": "9020",
    "priceRate": "0.3",
    "updateTime": 1571110484038,
    "workingType": "CONTRACT_PRICE",
    "priceProtect": false,
    "priceMatch": "NONE",
    "selfTradePreventionMode": "NONE",
    "goodTillDate": 1693207680000
  },
  {"code": -2011, "msg": "Unknown order sent."}
]
```

### Cancel All Open Orders (Symbol)
- Category: Trade  
- Endpoint: `DELETE /fapi/v1/allOpenOrders`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-All-Open-Orders  
- Description: Cancel all open orders for a symbol.  
- Parameters: `symbol`, `recvWindow`, `timestamp`.  
- Response example:

```json
{"code": 200, "msg": "The operation of cancel all open order is done."}
```

### Auto Cancel All Open Orders (Countdown)
- Category: Trade  
- Endpoint: `POST /fapi/v1/countdownCancelAll`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Auto-Cancel-All-Open-Orders  
- Description: Set a countdown to cancel all open orders on a symbol.  
- Parameters: `symbol`, `countdownTime`, `recvWindow`, `timestamp`.  
- Response example:

```json
{"symbol": "BTCUSDT", "countdownTime": "100000"}
```

### Query Current Open Order
- Category: Trade  
- Endpoint: `GET /fapi/v1/openOrder`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Query-Current-Open-Order  
- Description: Query a specific open order.  
- Parameters: `symbol` + `orderId` or `origClientOrderId`.  
- Response example:

```json
{
  "avgPrice": "0.00000",
  "clientOrderId": "abc",
  "cumQuote": "0",
  "executedQty": "0",
  "orderId": 1917641,
  "origQty": "0.40",
  "origType": "TRAILING_STOP_MARKET",
  "price": "0",
  "reduceOnly": false,
  "side": "BUY",
  "positionSide": "SHORT",
  "status": "NEW",
  "stopPrice": "9300",
  "closePosition": false,
  "symbol": "BTCUSDT",
  "time": 1579276756075,
  "timeInForce": "GTC",
  "type": "TRAILING_STOP_MARKET",
  "activatePrice": "9020",
  "priceRate": "0.3",
  "updateTime": 1579276756075,
  "workingType": "CONTRACT_PRICE",
  "priceProtect": false,
  "priceMatch": "NONE",
  "selfTradePreventionMode": "NONE",
  "goodTillDate": 0
}
```

### Query Current All Open Orders
- Category: Trade  
- Endpoint: `GET /fapi/v1/openOrders`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-All-Open-Orders  
- Description: List open orders; careful without `symbol`.  
- Parameters: optional `symbol`.  
- Response example:

```json
[
  {
    "avgPrice": "0.00000",
    "clientOrderId": "abc",
    "cumQuote": "0",
    "executedQty": "0",
    "orderId": 1917641,
    "origQty": "0.40",
    "origType": "TRAILING_STOP_MARKET",
    "price": "0",
    "reduceOnly": false,
    "side": "BUY",
    "positionSide": "SHORT",
    "status": "NEW",
    "stopPrice": "9300",
    "closePosition": false,
    "symbol": "BTCUSDT",
    "time": 1579276756075,
    "timeInForce": "GTC",
    "type": "TRAILING_STOP_MARKET",
    "activatePrice": "9020",
    "priceRate": "0.3",
    "updateTime": 1579276756075,
    "workingType": "CONTRACT_PRICE",
    "priceProtect": false,
    "priceMatch": "NONE",
    "selfTradePreventionMode": "NONE",
    "goodTillDate": 0
  }
]
```

### Query All Orders (History)
- Category: Trade  
- Endpoint: `GET /fapi/v1/allOrders`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/All-Orders  
- Description: All account orders (active/canceled/filled).  
- Parameters: `symbol`, optional filters.  
- Response example:

```json
[
  {
    "avgPrice": "0.00000",
    "clientOrderId": "abc",
    "cumQuote": "0",
    "executedQty": "0",
    "orderId": 1917641,
    "origQty": "0.40",
    "origType": "TRAILING_STOP_MARKET",
    "price": "0",
    "reduceOnly": false,
    "side": "BUY",
    "positionSide": "SHORT",
    "status": "NEW",
    "stopPrice": "9300",
    "closePosition": false,
    "symbol": "BTCUSDT",
    "time": 1579276756075,
    "timeInForce": "GTC",
    "type": "TRAILING_STOP_MARKET",
    "activatePrice": "9020",
    "priceRate": "0.3",
    "updateTime": 1579276756075,
    "workingType": "CONTRACT_PRICE",
    "priceProtect": false,
    "priceMatch": "NONE",
    "selfTradePreventionMode": "NONE",
    "goodTillDate": 0
  }
]
```

### Algo Orders (Migration Notice)
- Category: Trade  
- Endpoints:  
  - `POST /fapi/v1/algoOrder` — place  
  - `DELETE /fapi/v1/algoOrder` — cancel  
  - `DELETE /fapi/v1/algoOpenOrders` — cancel all open algo orders  
  - `GET /fapi/v1/algoOrder` — query  
  - `GET /fapi/v1/openAlgoOrders` — open algo orders  
  - `GET /fapi/v1/allAlgoOrders` — history  
- URL: developers.binance.com/docs/derivatives/change-log (USDⓈ-M Futures — 2025-11-06)  
- Description: Conditional orders migrated to Algo Service; some types blocked on legacy endpoints with `-4120`.

---

## REST — Account & Positions

### Account Information (V2)
- Category: Account  
- Endpoint: `GET /fapi/v2/account`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V2  
- Description: Account info (single-asset/multi-assets).  
- Response example:

```json
{
  "feeTier": 0,
  "feeBurn": true,
  "canTrade": true,
  "canDeposit": true,
  "canWithdraw": true,
  "updateTime": 0,
  "multiAssetsMargin": false,
  "tradeGroupId": -1,
  "totalInitialMargin": "0.00000000",
  "totalMaintMargin": "0.00000000",
  "totalWalletBalance": "23.72469206",
  "totalUnrealizedProfit": "0.00000000",
  "totalMarginBalance": "23.72469206",
  "totalPositionInitialMargin": "0.00000000",
  "totalOpenOrderInitialMargin": "0.00000000",
  "totalCrossWalletBalance": "23.72469206",
  "totalCrossUnPnl": "0.00000000",
  "availableBalance": "23.72469206",
  "maxWithdrawAmount": "23.72469206",
  "assets": [
    {
      "asset": "USDT",
      "walletBalance": "23.72469206",
      "unrealizedProfit": "0.00000000",
      "marginBalance": "23.72469206",
      "maintMargin": "0.00000000",
      "initialMargin": "0.00000000",
      "positionInitialMargin": "0.00000000",
      "openOrderInitialMargin": "0.00000000",
      "crossWalletBalance": "23.72469206",
      "crossUnPnl": "0.00000000",
      "availableBalance": "23.72469206",
      "maxWithdrawAmount": "23.72469206",
      "marginAvailable": true,
      "updateTime": 1625474304765
    }
  ],
  "positions": [
    {
      "symbol": "BTCUSDT",
      "initialMargin": "0",
      "maintMargin": "0",
      "unrealizedProfit": "0.00000000",
      "positionInitialMargin": "0",
      "openOrderInitialMargin": "0",
      "leverage": "100",
      "isolated": true,
      "entryPrice": "0.00000",
      "maxNotional": "250000",
      "bidNotional": "0",
      "askNotional": "0",
      "positionSide": "BOTH",
      "positionAmt": "0",
      "updateTime": 0
    }
  ]
}
```

### Account Information (V3)
- Category: Account  
- Endpoint: `GET /fapi/v3/account`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V3  
- Description: Account info (expanded fields; USD normalization).  
- Response example: shown in doc.

### Futures Account Balance (V2)
- Category: Account  
- Endpoint: `GET /fapi/v2/balance`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Futures-Account-Balance-V2  
- Description: Asset balances, available, max withdraw.  
- Response example:

```json
[
  {
    "accountAlias": "SgsR",
    "asset": "USDT",
    "balance": "122607.35137903",
    "crossWalletBalance": "23.72469206",
    "crossUnPnl": "0.00000000",
    "availableBalance": "23.72469206",
    "maxWithdrawAmount": "23.72469206",
    "marginAvailable": true,
    "updateTime": 1617939110373
  }
]
```

### Futures Account Balance (V3)
- Category: Account  
- Endpoint: `GET /fapi/v3/balance`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Futures-Account-Balance-V3  
- Description: Asset balances (V3 schema).  
- Response example: shown in doc.

### Notional & Leverage Brackets
- Category: Account  
- Endpoint: `GET /fapi/v1/leverageBracket`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Notional-and-Leverage-Brackets  
- Description: Per-symbol leverage brackets and maintenance ratios.  
- Response example:

```json
[
  {
    "symbol": "ETHUSDT",
    "notionalCoef": 1.5,
    "brackets": [
      {
        "bracket": 1,
        "initialLeverage": 75,
        "notionalCap": 10000,
        "notionalFloor": 0,
        "maintMarginRatio": 0.0065,
        "cum": 0.0
      }
    ]
  }
]
```

### Change Initial Leverage
- Category: Account  
- Endpoint: `POST /fapi/v1/leverage`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Initial-Leverage  
- Description: Set initial leverage for a symbol.  
- Parameters: `symbol`, `leverage` (1–125), `recvWindow`, `timestamp`.  
- Response example:

```json
{"leverage": 21, "maxNotionalValue": "1000000", "symbol": "BTCUSDT"}
```

### Position Information (V2)
- Category: Positions  
- Endpoint: `GET /fapi/v2/positionRisk`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Position-Information-V2  
- Description: Position risk details per symbol/side.  
- Response example:

```json
[
  {
    "symbol": "BTCUSDT",
    "positionAmt": "0.001",
    "entryPrice": "22185.2",
    "breakEvenPrice": "0.0",
    "markPrice": "21123.05052574",
    "unRealizedProfit": "-1.06214947",
    "liquidationPrice": "19731.45529116",
    "leverage": "4",
    "maxNotionalValue": "100000000",
    "marginType": "cross",
    "isolatedMargin": "0.00000000",
    "isAutoAddMargin": "false",
    "positionSide": "LONG",
    "notional": "21.12305052",
    "isolatedWallet": "0",
    "updateTime": 1655217461579
  },
  {
    "symbol": "BTCUSDT",
    "positionAmt": "0.000",
    "entryPrice": "0.0",
    "breakEvenPrice": "0.0",
    "markPrice": "21123.05052574",
    "unRealizedProfit": "0.00000000",
    "liquidationPrice": "0",
    "leverage": "4",
    "maxNotionalValue": "100000000",
    "marginType": "cross",
    "isolatedMargin": "0.00000000",
    "isAutoAddMargin": "false",
    "positionSide": "SHORT",
    "notional": "0",
    "isolatedWallet": "0",
    "updateTime": 0
  }
]
```

### Position Margin Change History
- Category: Positions  
- Endpoint: `GET /fapi/v1/positionMargin/history`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Get-Position-Margin-Change-History  
- Description: History of position margin changes.  
- Response example: shown in doc.

### Classic Portfolio Margin Account Info
- Category: Portfolio Margin  
- Endpoint: `GET /fapi/v1/pmAccountInfo`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/portfolio-margin-endpoints  
- Description: Classic Portfolio Margin current account info.  
- Parameters: `asset`, optional `recvWindow`, `timestamp`.  
- Response example: shown in doc.

---

## REST — User Data Streams

### Start User Data Stream
- Category: User Data (REST)  
- Endpoint: `POST /fapi/v1/listenKey`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams  
- Description: Create/return active `listenKey`. Valid 60 minutes; extended on POST.

### Keepalive User Data Stream
- Category: User Data (REST)  
- Endpoint: `PUT /fapi/v1/listenKey`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams/Keepalive-User-Data-Stream  
- Description: Extend `listenKey` validity by 60 minutes.  
- Response example:

```json
{"listenKey": "3HBntNTepshgEdjIwSUIBgB9keLyOCg5qv3n6bYAtktG8ejcaW5HXz9Vx1JgIieg"}
```

### Close User Data Stream
- Category: User Data (REST)  
- Endpoint: `DELETE /fapi/v1/listenKey`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams  
- Description: Invalidate and close the stream.

### WebSocket API — Start/Keepalive
- Category: User Data (WebSocket API)  
- Methods: `userDataStream.start`, `userDataStream.ping`  
- URL:  
  - Start: developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams/Start-User-Data-Stream-Wsp  
  - Keepalive: developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams/Keepalive-User-Data-Stream-Wsp  
- Description: Manage `listenKey` via WebSocket API methods.  
- Response examples: shown in doc.

---

## WebSocket — Market Streams

### Connection & Limits
- Base WS: `wss://fstream.binance.com`  
- Raw stream: `/ws/<streamName>`; Combined: `/stream?streams=<s1>/<s2>`  
- Max 1024 streams per connection; 10 incoming messages/sec; ping every 3 min; disconnect at 24h.

URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams

### Aggregate Trade Streams
- Stream: `<symbol>@aggTrade`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Aggregate-Trade-Streams  
- Payload example:

```json
{
  "e": "aggTrade",
  "E": 123456789,
  "s": "BTCUSDT",
  "a": 5933014,
  "p": "0.001",
  "q": "100",
  "f": 100,
  "l": 105,
  "T": 123456785,
  "m": true
}
```

### Liquidation Order Streams (Symbol)
- Stream: `<symbol>@forceOrder`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams  
- Payload example:

```json
{
  "e": "forceOrder",
  "E": 1568014460893,
  "o": {
    "s": "BTCUSDT",
    "S": "SELL",
    "o": "LIMIT",
    "f": "IOC",
    "q": "0.014",
    "p": "9910",
    "ap": "9910",
    "X": "FILLED",
    "l": "0.014",
    "z": "0.014",
    "T": 1568014460893
  }
}
```

### All Market Liquidation Order Streams
- Stream: `!forceOrder@arr`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Liquidation-Order-Streams  
- Payload: snapshots across all symbols.

### Partial Book Depth Streams
- Stream: `<symbol>@depth<levels>`, `<symbol>@depth<levels>@500ms`, `<symbol>@depth<levels>@100ms`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Partial-Book-Depth-Streams  
- Payload example:

```json
{
  "e": "depthUpdate",
  "E": 1571889248277,
  "T": 1571889248276,
  "s": "BTCUSDT",
  "U": 390497796,
  "u": 390497878,
  "pu": 390497794,
  "b": [["7403.89", "0.002"], ["7403.90", "3.906"]],
  "a": [["7405.96", "3.340"], ["7406.63", "4.525"]]
}
```

### Diff Book Depth Streams
- Stream: `<symbol>@depth`, `<symbol>@depth@500ms`, `<symbol>@depth@100ms`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Diff-Book-Depth-Streams  
- Payload: frequent `depthUpdate` diffs.

### Individual Symbol Mini Ticker
- Stream: `<symbol>@miniTicker`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Mini-Ticker-Stream  
- Payload: 24hr rolling window mini-ticker.

### Individual Symbol 24hr Ticker
- Stream: `<symbol>@ticker`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Ticker-Streams  
- Payload: 24hr rolling window ticker stats.

### All Market 24hr Tickers
- Stream: `!ticker@arr`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Tickers-Streams  
- Payload: array of changed tickers.

### Mark Price Stream
- Stream: `<symbol>@markPrice`, `<symbol>@markPrice@1s`; All symbols: `!markPrice@arr`, `!markPrice@arr@1s`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Mark-Price-Stream  
- Payload example:

```json
{
  "e": "markPriceUpdate",
  "E": 1562305380000,
  "s": "BTCUSDT",
  "p": "11794.15000000",
  "i": "11784.62659091",
  "P": "11784.25641265",
  "r": "0.00038167",
  "T": 1562306400000
}
```

### Local Order Book Management Guide
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly  
- Note: Use REST snapshot `GET /fapi/v1/depth?symbol=...&limit=1000` then apply WS events with `U/u/pu` sequence rules.

---

## REST — Convert (USDⓈ-M Futures)

### List All Convert Pairs
- Category: Convert  
- Endpoint: `GET /fapi/v1/convert/exchangeInfo`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/convert  
- Description: Query convertible token pairs and per-asset min/max amounts.  
- Parameters: optional `fromAsset`, `toAsset`.  
- Response example:

```json
[
  {
    "fromAsset":"BTC",
    "toAsset":"USDT",
    "fromAssetMinAmount":"0.0004",
    "fromAssetMaxAmount":"50",
    "toAssetMinAmount":"20",
    "toAssetMaxAmount":"2500000"
  }
]
```

### Get Quote
- Category: Convert  
- Endpoint: `POST /fapi/v1/convert/getQuote`  
- URL: developers.binance.com/docs/derivatives/change-log  
- Description: Request a conversion quote. Valid time is 10s.  

### Accept Quote
- Category: Convert  
- Endpoint: `POST /fapi/v1/convert/acceptQuote`  
- URL: developers.binance.com/docs/derivatives/change-log  
- Description: Accept a previously received quote.

### Order Status
- Category: Convert  
- Endpoint: `GET /fapi/v1/convert/orderStatus`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/convert/Order-Status  
- Description: Query convert order by `orderId` or `quoteId`.  
- Parameters: `orderId` or `quoteId`.  
- Response example:

```json
{
  "orderId":933256278426274426,
  "orderStatus":"SUCCESS",
  "fromAsset":"BTC",
  "fromAmount":"0.00054414",
  "toAsset":"USDT",
  "toAmount":"20",
  "ratio":"36755",
  "inverseRatio":"0.00002721",
  "createTime":1623381330472
}
```

---

## Portfolio Margin — General

- Base REST: `https://papi.binance.com`  
- URL: developers.binance.com/docs/derivatives/portfolio-margin/general-info  
- Notes: Portfolio Margin rate limits differ; error-handling semantics mirror Futures General Info.  

### Classic Portfolio Margin Account Info (USDⓈ-M)
- See: Classic Portfolio Margin section above: `GET /fapi/v1/pmAccountInfo`  
- URL: developers.binance.com/docs/derivatives/usds-margined-futures/portfolio-margin-endpoints

### UM Portfolio Margin Account
- Category: Portfolio Margin  
- Endpoint: `GET /papi/v1/um/account`  
- URL: developers.binance.com/docs/derivatives/portfolio-margin/account  
- Description: Portfolio Margin unified account balances and fields (includes `tradeGroupId`).

---

## Change Log Highlights (USDⓈ-M)
- New endpoints: `GET /fapi/v1/commissionRate`, `GET /fapi/v1/rpiDepth`.  
- New streams: `<symbol>@rpiDepth@500ms`.  
- ADL risk rating: `GET /fapi/v1/symbolAdlRisk`.  
- Algo order endpoints (see Trade section).  
- RPI order behavior and visibility exclusions.  
- Symbol Chinese encoding support; URL-encode non-ASCII symbols.  
- Error message update for `-1008`.

Source: Change Log (developers.binance.com/docs/derivatives/change-log)

---

## User Data Streams — Connection
- REST create/keepalive/delete per above; WS path: `/ws/<listenKey>`.  
- One connection guarantees ordered payloads during heavy periods; recommend ordering by `E`.  
- Disconnect at 24h; re-establish.

URL: developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams

---

## Notes
- Only endpoints and streams referenced directly from official docs are listed.  
- For parameters not fully enumerated above, consult the linked pages.  
- WebSocket API (orders via WS) is separate from Market Data WS; see Change Log for availability and base `wss://ws-fapi.binance.com/ws-fapi/v1`.
