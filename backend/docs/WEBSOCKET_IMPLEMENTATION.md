# WebSocket Implementation

This document describes the WebSocket implementation for real-time trading platform features.

## Overview

The WebSocket implementation provides real-time communication between clients and the trading platform, enabling live updates for:
- Price feeds and market data
- Order updates and execution status
- Risk alerts and notifications
- Bot status and performance metrics
- Portfolio changes

## Architecture

### Components

1. **WebSocket Manager** (`websocket_manager.py`)
   - High-level WebSocket operations
   - Message routing and broadcasting
   - User authentication and authorization
   - Stream subscription management

2. **Connection Manager** (`connection_manager.py`)
   - WebSocket connection lifecycle
   - User session management
   - Subscription tracking
   - Message delivery

3. **Binance Stream Client** (`binance_stream.py`)
   - Binance WebSocket integration
   - Market data streaming
   - Price feed processing
   - Order book and trade data

4. **WebSocket Controller** (`websocket_controller.py`)
   - FastAPI WebSocket endpoints
   - Authentication handling
   - Message validation and routing

5. **WebSocket Service** (`websocket_service.py`)
   - Application lifecycle management
   - Service orchestration
   - Health monitoring

## Endpoints

### 1. Trading WebSocket (`/ws/trading`)

**Authentication Required**: Yes (JWT token)

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/trading?token=YOUR_JWT_TOKEN');
```

#### Supported Messages

**Subscribe to Channels**
```json
{
  "type": "subscribe",
  "channels": ["orders", "risk_alerts", "bot_status", "portfolio"]
}
```

**Subscribe to Symbol Price Updates**
```json
{
  "type": "subscribe_symbol",
  "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
}
```

**Unsubscribe from Channels**
```json
{
  "type": "unsubscribe",
  "channels": ["orders"]
}
```

**Ping/Pong for Connection Health**
```json
{
  "type": "ping"
}
```

#### Server Messages

**Order Updates**
```json
{
  "type": "order_update",
  "order_id": "123456",
  "status": "filled",
  "filled_quantity": "0.5",
  "remaining_quantity": "0",
  "average_price": "50000.00",
  "timestamp": "2023-12-01T12:00:00Z"
}
```

**Risk Alerts**
```json
{
  "type": "risk_alert",
  "alert_type": "position_limit_exceeded",
  "severity": "high",
  "message": "Position limit exceeded for BTCUSDT",
  "limit_value": "10000",
  "current_value": "12000",
  "timestamp": "2023-12-01T12:00:00Z"
}
```

**Bot Status Updates**
```json
{
  "type": "bot_status",
  "bot_id": "bot-123",
  "name": "DCA Bot",
  "status": "running",
  "performance": {
    "total_pnl": "250.50",
    "win_rate": "65.5",
    "trades_today": 15
  },
  "timestamp": "2023-12-01T12:00:00Z"
}
```

### 2. Market Data WebSocket (`/ws/market`)

**Authentication Required**: No (Public endpoint)

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/market');
```

#### Supported Messages

**Subscribe to Ticker Updates**
```json
{
  "type": "subscribe_ticker",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Subscribe to Trade Updates**
```json
{
  "type": "subscribe_trades",
  "symbols": ["BTCUSDT"]
}
```

**Subscribe to Order Book Updates**
```json
{
  "type": "subscribe_orderbook",
  "symbols": ["BTCUSDT"]
}
```

#### Server Messages

**Price Updates**
```json
{
  "type": "ticker",
  "symbol": "BTCUSDT",
  "price": "50000.00",
  "price_change": "1250.00",
  "price_change_percent": "2.56",
  "high_price": "51000.00",
  "low_price": "48500.00",
  "volume": "1250.75",
  "timestamp": "2023-12-01T12:00:00Z"
}
```

**Trade Updates**
```json
{
  "type": "trade",
  "symbol": "BTCUSDT",
  "price": "50000.00",
  "quantity": "0.1",
  "side": "buy",
  "timestamp": "2023-12-01T12:00:00Z"
}
```

**Order Book Updates**
```json
{
  "type": "orderbook",
  "symbol": "BTCUSDT",
  "bids": [
    ["49950.00", "1.5"],
    ["49940.00", "2.1"]
  ],
  "asks": [
    ["50050.00", "1.2"],
    ["50060.00", "0.8"]
  ],
  "timestamp": "2023-12-01T12:00:00Z"
}
```

## Usage Examples

### Frontend Integration

```javascript
class TradingWebSocket {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/ws/trading?token=${this.token}`);
    
    this.ws.onopen = () => {
      console.log('Connected to trading WebSocket');
      this.reconnectAttempts = 0;
      this.subscribeToUpdates();
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket connection closed');
      this.attemptReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  subscribeToUpdates() {
    // Subscribe to order updates
    this.send({
      type: 'subscribe',
      channels: ['orders', 'risk_alerts', 'bot_status']
    });
    
    // Subscribe to price updates for watched symbols
    this.send({
      type: 'subscribe_symbol',
      symbols: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    });
  }

  handleMessage(message) {
    switch (message.type) {
      case 'order_update':
        this.updateOrderStatus(message);
        break;
      case 'risk_alert':
        this.showRiskAlert(message);
        break;
      case 'ticker':
        this.updatePriceDisplay(message);
        break;
      case 'pong':
        console.log('Received pong');
        break;
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
    }
  }
}

// Initialize WebSocket connection
const tradingWS = new TradingWebSocket(userToken);
tradingWS.connect();
```

### Python Client Example

```python
import asyncio
import json
import websockets

async def trading_client(token):
    uri = f"ws://localhost:8000/ws/trading?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to updates
        await websocket.send(json.dumps({
            "type": "subscribe",
            "channels": ["orders", "risk_alerts"]
        }))
        
        # Listen for messages
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received: {data}")

# Run the client
asyncio.run(trading_client("your_jwt_token"))
```

## Testing

### Manual Testing

Use the provided test client:

```bash
# Test market data WebSocket (public)
python tools/websocket_test_client.py --test market

# Test trading WebSocket (requires token)
python tools/websocket_test_client.py --test trading --token YOUR_JWT_TOKEN

# Test connection health
python tools/websocket_test_client.py --test health

# Run all tests
python tools/websocket_test_client.py --test all --token YOUR_JWT_TOKEN
```

### Unit Tests

```bash
# Run WebSocket tests
pytest tests/integration/test_websocket.py -v

# Run with coverage
pytest tests/integration/test_websocket.py --cov=trading.infrastructure.websocket
```

## Configuration

WebSocket settings are configured in the application settings:

```python
# settings.py
class Settings:
    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_RECONNECT_TIMEOUT: int = 60  # seconds
```

## Error Handling

### Connection Errors

- **4001**: Authentication required or invalid token
- **4002**: User not found or inactive
- **4003**: Maximum connections exceeded
- **4004**: Invalid message format

### Message Format

Error messages follow this format:

```json
{
  "type": "error",
  "code": 4001,
  "message": "Authentication token required",
  "timestamp": "2023-12-01T12:00:00Z"
}
```

## Performance Considerations

1. **Connection Limits**: Each user can have up to 5 concurrent WebSocket connections
2. **Message Throttling**: Messages are rate-limited to prevent spam
3. **Memory Usage**: Connection state is stored in memory for fast access
4. **Scalability**: Consider Redis for session storage in multi-instance deployments

## Security

1. **Authentication**: JWT token validation for trading endpoints
2. **Authorization**: User-specific data isolation
3. **Rate Limiting**: Protection against message flooding
4. **Input Validation**: All incoming messages are validated

## Monitoring

### Health Check

```bash
curl http://localhost:8000/ws/status
```

Response:
```json
{
  "status": "active",
  "active_connections": 15,
  "user_connections": {
    "user_123": 2,
    "user_456": 1
  },
  "total_subscriptions": 25
}
```

### Metrics

- Active connection count
- Messages per second
- Subscription distribution
- Error rates
- Connection duration

## Deployment

### Docker

The WebSocket server runs as part of the main FastAPI application:

```dockerfile
# WebSocket ports are handled by the main application
EXPOSE 8000
```

### Load Balancing

For multiple instances, use sticky sessions or implement Redis-based session storage:

```nginx
upstream websocket_backend {
    ip_hash;  # Sticky sessions
    server backend1:8000;
    server backend2:8000;
}
```

## Future Enhancements

1. **Redis Integration**: For distributed session management
2. **Message Persistence**: Store and replay missed messages
3. **Advanced Filtering**: Complex subscription filters
4. **GraphQL Subscriptions**: Alternative to custom WebSocket protocol
5. **Binary Protocol**: For high-frequency trading applications