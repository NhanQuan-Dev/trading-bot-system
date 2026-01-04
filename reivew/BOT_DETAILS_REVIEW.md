## Total P&L Figure

**Logic:** 

Total P&L = Tổng P&L của *tất cả trades đã được đóng* (closed trades) mà bot đó thực hiện. Không tính unrealized P&L của các vị thế đang mở, trừ khi có yêu cầu riêng.

**Real-time update:**

Real-time được hiểu là: khi có trade mới được đóng hoặc trade cũ được cập nhật P&L (partial close, fee update, funding update) thì Total P&L phải được push ngay tới UI thông qua event-driven mechanism (WebSocket / SSE / PubSub), không chờ user reload page.

**Pause thì có real-time không?**

Có, nhưng cần phân biệt rõ:

- Khi bot Pause: bot **không mở trade mới**
- Nhưng các trade đã mở trước đó **vẫn có thể đóng / bị liquidate / bị stop**
    
    → Vì vậy **vẫn phải real-time update** cho tới khi tất cả trades của bot đều closed.
    

**Consistency (Bot Details vs Bot Management):**

Hai màn hình phải subscribe cùng một nguồn dữ liệu (shared projection / cached aggregate), không được tính toán riêng ở frontend.

## Win Rate Figure

**Logic:** 

Win Rate = (Số trades có realized P&L > 0) / (Tổng số trades đã closed)

**Real-time update:**

Win Rate update cùng thời điểm với Total P&L, tức là:

- Khi có trade mới closed
- Khi trạng thái trade đổi từ open → closed
- Khi realized P&L của trade được điều chỉnh lại

**Pause thì có real-time không?**

Có, nhưng cần phân biệt rõ:

- Khi bot Pause: bot **không mở trade mới**
- Nhưng các trade đã mở trước đó **vẫn có thể đóng / bị liquidate / bị stop**
    
    → Vì vậy **vẫn phải real-time update** cho tới khi tất cả trades của bot đều closed.
    

**Consistency (Bot Details vs Bot Management):**

Hai màn hình phải subscribe cùng một nguồn dữ liệu (shared projection / cached aggregate), không được tính toán riêng ở frontend.

## Total Trades Figure (Win/Loss)

**Logic**

Total Trades = Tổng số trades đã closed

Win Trades = số trades có realized P&L ≥ 0

Loss Trades = số trades có realized P&L < 0

**Real-time update:**

- Ngay khi trade đóng → increment counter
- Không phụ thuộc chart, không polling DB mỗi X giây

**Pause thì có real-time không?**

Có, nhưng cần phân biệt rõ:

- Khi bot Pause: bot **không mở trade mới**
- Nhưng các trade đã mở trước đó **vẫn có thể đóng / bị liquidate / bị stop**
    
    → Vì vậy **vẫn phải real-time update** cho tới khi tất cả trades của bot đều closed.
    

**Consistency (Bot Details vs Bot Management):**

Hai màn hình phải subscribe cùng một nguồn dữ liệu (shared projection / cached aggregate), không được tính toán riêng ở frontend.

## Streak Figure (Win/Loss)

**Logic**

Win Streak = số trade thắng liên tiếp đã từng

Loss Streak = số trade thua liên tiếp đã từng

Chỉ tính trên trades đã closed

**Real-time update**

Chỉ update khi có trade mới closed. Không cần update khi giá chạy.

**Pause thì có real-time không?**

Có, nhưng cần phân biệt rõ:

- Khi bot Pause: bot **không mở trade mới**
- Nhưng các trade đã mở trước đó **vẫn có thể đóng / bị liquidate / bị stop**
    
    → Vì vậy **vẫn phải real-time update** cho tới khi tất cả trades của bot đều closed.
    

**Consistency (Bot Details vs Bot Management):**

Hai màn hình phải subscribe cùng một nguồn dữ liệu (shared projection / cached aggregate), không được tính toán riêng ở frontend.

---

# Implementation Readiness Analysis

**Reviewed:** 2025-12-25  
**Status:** ⚠️ **CHƯA ĐỦ ĐIỀU KIỆN IMPLEMENT** - Cần bổ sung nhiều thành phần

---

## Tổng quan hiện trạng

| Component | Status | Notes |
|-----------|--------|-------|
| Database Schema | ⚠️ Partial | Có `BotPerformanceModel` (daily) nhưng thiếu cumulative stats |
| Domain Events | ⚠️ Partial | Có `PositionClosedEvent` nhưng chưa wire đến bot stats |
| Trade Entity | ❌ Missing | Không có Trade domain entity, chỉ có Position & Order |
| WebSocket Infrastructure | ⚠️ Partial | Có `broadcast_bot_status_update`, thiếu trade event |
| Frontend Real-time | ❌ Missing | Dùng mock data, không có WebSocket subscription |
| Streak Tracking | ❌ Missing | Không có field nào liên quan đến streak |

---

## Chi tiết từng yêu cầu

### 1. Total P&L Figure

| Item | Current State | Gap |
|------|--------------|-----|
| **Database** | `BotPerformanceModel.cumulative_pnl` (daily) | ❌ Thiếu `total_pnl` aggregate trên `BotModel` |
| **API** | Không có endpoint trả `total_pnl` | ❌ Cần thêm computed field hoặc materialized view |
| **Real-time** | `broadcast_bot_status_update()` exists | ⚠️ Chưa gọi khi trade closed |
| **Frontend** | `bot.total_pnl` trong type | ⚠️ Nhưng data từ API chưa có, dùng mock |

**Files liên quan:**
- [bot_models.py](file:///home/qwe/Desktop/zxc/backend/src/trading/infrastructure/persistence/models/bot_models.py) - Lines 51, 165-166
- [websocket_manager.py](file:///home/qwe/Desktop/zxc/backend/src/trading/infrastructure/websocket/websocket_manager.py) - Lines 250-266
- [bot.ts](file:///home/qwe/Desktop/zxc/frontend/src/lib/types/bot.ts) - Line 48

### 2. Win Rate Figure

| Item | Current State | Gap |
|------|--------------|-----|
| **Database** | `BotPerformanceModel.win_rate` (daily only) | ❌ Thiếu cumulative win_rate trên `BotModel` |
| **Calculation Logic** | Không có service tính win_rate | ❌ Cần service aggregate từ closed positions |
| **Frontend** | `bot.win_rate` trong type | ⚠️ Dùng mock data |

**Files liên quan:**
- [bot_models.py](file:///home/qwe/Desktop/zxc/backend/src/trading/infrastructure/persistence/models/bot_models.py) - Line 167
- [bot.ts](file:///home/qwe/Desktop/zxc/frontend/src/lib/types/bot.ts) - Lines 29, 49

### 3. Total Trades Figure (Win/Loss)

| Item | Current State | Gap |
|------|--------------|-----|
| **Database** | `BotPerformanceModel` có daily: `trades_count`, `winning_trades`, `losing_trades` | ❌ Thiếu cumulative trên `BotModel` |
| **Trade Entity** | **KHÔNG TỒN TẠI** | ❌ Chỉ có `Order` và `Position`, cần định nghĩa Trade là gì |
| **Counting Logic** | Không có | ❌ Cần xác định: 1 trade = 1 position close? Hay = pair of orders? |

**Files liên quan:**
- [bot_models.py](file:///home/qwe/Desktop/zxc/backend/src/trading/infrastructure/persistence/models/bot_models.py) - Lines 160-162
- [BotDetail.tsx](file:///home/qwe/Desktop/zxc/frontend/src/pages/BotDetail.tsx) - Lines 301-303

### 4. Streak Figure (Win/Loss)

| Item | Current State | Gap |
|------|--------------|-----|
| **Database** | ❌ Không có field nào | ❌ Cần thêm `current_win_streak`, `current_loss_streak`, `max_win_streak`, `max_loss_streak` |
| **Calculation Logic** | ❌ Không có | ❌ Cần track sequential wins/losses |
| **Frontend** | ❌ Không có trong type | ❌ Cần thêm vào `Bot` type và UI |

---

## Domain & Infrastructure Gaps

### A. Trade Entity ✅ DEFINED

**Decision:** Trade = Position Closed

Hiện tại hệ thống có:
- `Order` - Lệnh đặt
- `Position` - Vị thế đang mở
- `PositionClosedEvent` - Event khi đóng position → **ĐÂY LÀ TRADE**

**Ý nghĩa:**
- 1 Trade = 1 Position được đóng (full hoặc partial close)
- Source of truth: `PositionClosedEvent` với `realized_pnl`
- Mỗi lần position close → emit event → update bot stats

**Không cần** tạo Trade entity mới, sử dụng `PositionClosedEvent` làm nguồn dữ liệu.

### B. Event-Driven Stats Update (CHƯA WIRE)

`PositionClosedEvent` có `realized_pnl` nhưng:
- ❌ Không có handler update `BotModel` stats
- ❌ Không có handler gọi `broadcast_bot_status_update()`

**File:** [position_closed_event.py](file:///home/qwe/Desktop/zxc/backend/src/trading/domain/portfolio/events/position_closed_event.py)

### C. WebSocket - Missing Trade Stream

```python
# Hiện có trong websocket_manager.py:
- broadcast_price_update()      ✅
- broadcast_order_update()      ✅  
- broadcast_risk_alert()        ✅
- broadcast_bot_status_update() ✅

# Cần thêm:
- broadcast_trade_update()      ❌ Missing
- broadcast_bot_stats_update()  ❌ Missing (khác với status)
```

### D. Frontend - No Real-time Integration

```tsx
// BotDetail.tsx hiện tại:
- Fetch data 1 lần khi mount
- Không subscribe WebSocket
- Tất cả positions/orders/trades đều là MOCK DATA

// Cần thêm:
- useWebSocket hook
- Subscribe bot stats stream
- Update state on WS message
```

---

## Checklist trước khi implement

### Backend

- [x] **Xác định Trade concept**: ✅ Trade = Position Close (dùng `PositionClosedEvent`)
- [ ] **Thêm fields vào `BotModel`**:
  - `total_pnl` (DECIMAL)
  - `total_trades` (INT)
  - `winning_trades` (INT)
  - `losing_trades` (INT)
  - `win_rate` (DECIMAL, computed hoặc denormalized)
  - `current_win_streak` (INT)
  - `current_loss_streak` (INT)
  - `max_win_streak` (INT)
  - `max_loss_streak` (INT)
- [ ] **Tạo Event Handler cho `PositionClosedEvent`**:
  - Update bot stats
  - Broadcast qua WebSocket
- [ ] **Thêm `broadcast_trade_update()` hoặc `broadcast_bot_stats_update()`** vào WebSocketManager
- [ ] **Tạo API endpoint** GET `/api/v1/bots/{id}/stats` (hoặc include trong bot detail)

### Frontend

- [ ] **Tạo `useWebSocket` hook** (hoặc dùng existing nếu có)
- [ ] **Update `Bot` type** với streak fields
- [ ] **Subscribe to bot stats stream** trong `BotDetail.tsx`
- [ ] **Loại bỏ mock data** và dùng real API/WebSocket

### Database

- [ ] **Migration** thêm columns vào `bots` table
- [ ] **Index** cho performance queries

---

## Kết luận

> [!WARNING]
> **Có thể bắt đầu implement** nhưng cần hoàn thành các bước chuẩn bị:
> 1. ✅ ~~Trade domain concept đã được định nghĩa~~ → **Trade = Position Close**
> 2. ❌ Event-driven flow chưa wire
> 3. ❌ Frontend chưa có real-time infrastructure

**Recommended next steps:**
1. ~~Clarify "Trade" definition với stakeholder~~ ✅ Done
2. Thêm required fields vào DB schema (migration)
3. Wire `PositionClosedEvent` → Bot stats update → WebSocket broadcast
4. Implement frontend WebSocket subscription