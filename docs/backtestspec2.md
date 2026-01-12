# Backtest Specification vs Implementation Analysis

File gốc: `docs/backtestspec.md`
Codebase: `backend/src/trading/infrastructure/backtesting/`

## 1. Multi-timeframe Core (1m source + HTF signal)

**Yêu cầu Spec:**
- Input: Dữ liệu 1m.
- Logic: Aggregate 1m -> HTF. Strategy chạy ở HTF Close.
- Execution: Replay 1m candle sau signal để khớp lệnh.

**Hiện trạng Code (`BacktestEngine`):**
- **Mismatch**: Engine hoạt động theo cơ chế "Candle-by-Candle" đơn giản.
- Method `run_backtest` nhận một list `candles` và loop qua từng candle.
- Không có logic nội tại để resample/aggregate từ 1m lên HTF.
- Nếu input là 1m, strategy chạy mỗi phút. Nếu input là 1h, strategy chạy mỗi giờ (mất độ chính xác intra-bar của 1m fill).

## 2. Setup-Trigger Model

**Yêu cầu Spec:**
- Tách biệt `SETUP_CONFIRMED` (HTF close) và `TRIGGER_HIT` (1m movement).
- State machine: Idle -> Setup Confirmed -> Waiting Trigger -> Filled/Expired.

**Hiện trạng Code:**
- **Mismatch**: Engine không có state machine cho Setup/Trigger.
- Engine nhận `signal` từ strategy và execute ngay lập tức (`_process_signal` gọi `_open_long_position` ngay).
- Không có concept "Waiting for Trigger" trong Engine. Logic này hiện tại (nếu có) phải do Strategy tự quản lý hoàn toàn, nhưng Engine không hỗ trợ native support (ví dụ: tự động check trigger trên 1m data giúp strategy).

## 3. Execution & Fill Engine

**Yêu cầu Spec:**
- FillPolicy: `optimistic` (chạm là fill), `neutral`, `strict` (wick filter, spread).
- Logic Limit chi tiết:
    - Buy Limit: `1m.open >= limit_price AND 1m.low <= limit_price`
    - Sell Limit: `1m.open <= limit_price AND 1m.high >= limit_price`
    - **Gap Detection**: Nếu open đã "nằm qua" giá limit theo hướng bất lợi → không fill.
- TP/SL xử lý:
    - Chỉ check **sau khi entry đã fill**.
    - **Price Path Assumption**: Nếu 1 candle chạm cả TP và SL → cần xử lý theo policy (configurable).
- Multi-order (Grid/DCA):
    - Thứ tự fill: Buy giá cao→thấp, Sell giá thấp→cao.
    - Kiểm tra margin/position constraints (không fill vượt vốn).

**Hiện trạng Code (`MarketSimulator`):**
- **Partial Match**:
    - Limit Fill: Có logic check `candle_low <= limit_price` cho LONG, `candle_high >= limit_price` cho SHORT.
    - **Missing Gap Detection**: Không kiểm tra điều kiện `open` để phát hiện gap qua giá limit.
    - **Missing FillPolicy Configuration**: Không có enum/config để chọn Optimistic/Neutral/Strict.
    - TP/SL Check: Có check trong `_check_sl_tp_trailing_with_high_low` dùng high/low.
    - **Missing Price Path Assumption**: Khi cả TP và SL cùng trigger trong 1 nến, code không có logic xử lý thứ tự (hiện tại check SL trước TP, nhưng không configurable và không document rõ assumption).
    - Multi-order: Engine hỗ trợ `add_long`/`add_short` (scale in).
    - **Missing Grid Logic**: Không có tự động quản lý grid orders với thứ tự fill.
    - **Missing Margin Constraints**: Không kiểm tra vốn khả dụng trước khi fill (có thể fill vượt initial capital).

## 4. Event-driven Logging

**Yêu cầu Spec:**
- Engine phải phát sinh Events:
    - `HTF_CANDLE_CLOSED`, `SETUP_CONFIRMED`, `SETUP_EXPIRED`
    - `ORDER_CREATED`, `ORDER_CANCELED`, `TRIGGER_HIT`
    - `ORDER_FILLED` (kèm policy + lý do fill/reject)
    - `TP_HIT`, `SL_HIT`
    - `POSITION_OPENED`, `POSITION_CLOSED`
- Trade record phải có:
    - `signal_time` (HTF close)
    - `entry_time` (LTF)
    - `entry_price`, `exit_time`, `exit_price`
    - `exit_reason` (TP/SL/Manual/Expired)
    - `max_drawdown`, `runup` (trong quá trình trade)
    - `execution_delay = entry_time - signal_time`
    - `fill_policy` + các điều kiện đã thỏa/miss
- Replay capability: Có thể replay/debug theo trade_id.

**Hiện trạng Code:**
- **Partial Match**:
    - Log cơ bản bằng Python `logger.debug/info`.
    - **Missing Event Architecture**: Không có event emitter/listener pattern. Events không được emit ra để external tools có thể listen.
    - Trade record (`BacktestTrade` entity):
        - ✅ Có: `entry_time`, `exit_time`, `entry_price`, `exit_price`, `exit_reason`
        - ❌ **Missing**: `signal_time` (thời điểm HTF close sinh signal)
        - ❌ **Missing**: `execution_delay` (delay từ signal đến entry)
        - ❌ **Missing**: `max_drawdown` (MDD trong suốt quá trình trade)
        - ❌ **Missing**: `runup` (unrealized profit cao nhất)
        - ❌ **Missing**: `fill_policy` (policy đã dùng để fill)
        - ❌ **Missing**: Các điều kiện fill đã thỏa/miss (để audit)
    - **Missing Replay**: Không có mechanism để replay lại 1 trade cụ thể theo trade_id (không lưu đủ snapshot data).

## Kết luận

Hệ thống hiện tại là một **Simple Event-Driven Engine** (chạy loop qua nến, giả lập khớp lệnh tại Close hoặc High/Low của nến đó).

Hệ thống **CHƯA** đáp ứng được spec **Advanced Multi-Timeframe 1m-Replay Engine** mà file `backtestspec.md` yêu cầu.

### Thiếu sót chính:

1. **Multi-Timeframe Architecture**: Không có dual-stream processing (1m data + HTF signal).
2. **Setup-Trigger State Machine**: Không có state để "pending" setup và tự động tìm trigger.
3. **Configurable Fill Policies**: Không có config Optimistic/Neutral/Strict.
4. **Gap Detection**: Không check open price để tránh fill ảo khi gap.
5. **Price Path Assumption**: Không xử lý conflict khi TP/SL cùng trigger.
6. **Grid/DCA Logic**: Không có auto-grid với thứ tự fill.
7. **Margin Validation**: Không validate vốn trước khi fill.
8. **Event Architecture**: Không emit events ra external listeners.
9. **Enhanced Trade Records**: Thiếu `signal_time`, `execution_delay`, `max_drawdown`, `runup`, `fill_policy`.
10. **Trade Replay**: Không có mechanism để replay debug theo trade_id.

---

## Backend và Frontend Changes

### 1. Create Backtest Flow

#### Backend Changes

**File: `backend/src/trading/application/backtesting/schemas.py`**

Thêm fields mới vào `BacktestConfigRequest`:
```python
class BacktestConfigRequest(BaseModel):
    # ... existing fields ...
    
    # NEW: Multi-timeframe settings
    data_timeframe: str = Field(default="1m", description="Data source timeframe (always 1m for spec)")
    signal_timeframe: str = Field(..., description="HTF for strategy signals (1h/4h/1d)")
    
    # NEW: Fill policy configuration
    fill_policy: FillPolicy = Field(
        default=FillPolicy.OPTIMISTIC,
        description="Fill policy: optimistic/neutral/strict"
    )
    
    # NEW: Price path assumption for TP/SL conflict
    price_path_assumption: PricePathAssumption = Field(
        default=PricePathAssumption.NEUTRAL,
        description="How to handle TP/SL conflict in same candle"
    )
    
    # NEW: Setup-Trigger settings
    enable_setup_trigger_model: bool = Field(
        default=False,
        description="Enable Setup-Trigger state machine"
    )
    setup_validity_window_minutes: int = Field(
        default=60,
        description="Setup validity window in minutes"
    )
```

**File: `backend/src/trading/domain/backtesting/enums.py`**

Thêm enums mới:
```python
class FillPolicy(str, Enum):
    OPTIMISTIC = "optimistic"  # chạm là fill
    NEUTRAL = "neutral"        # cross + filter cơ bản
    STRICT = "strict"          # cross + wick filter + spread

class PricePathAssumption(str, Enum):
    NEUTRAL = "neutral"        # SL trước TP
    OPTIMISTIC = "optimistic"  # TP trước SL
    REALISTIC = "realistic"    # Dựa vào open direction
```

#### Frontend Changes

**File: `frontend/src/pages/Backtest.tsx`**

Thêm form fields vào Create Backtest dialog:
```tsx
// Trong form state
const [fillPolicy, setFillPolicy] = useState<'optimistic' | 'neutral' | 'strict'>('optimistic');
const [signalTimeframe, setSignalTimeframe] = useState<string>('1h');
const [enableSetupTrigger, setEnableSetupTrigger] = useState(false);

// UI Components
<Select value={signalTimeframe} onValueChange={setSignalTimeframe}>
  <SelectTrigger>
    <SelectValue placeholder="Signal Timeframe" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="1h">1 Hour</SelectItem>
    <SelectItem value="4h">4 Hours</SelectItem>
    <SelectItem value="1d">1 Day</SelectItem>
  </SelectContent>
</Select>

<Select value={fillPolicy} onValueChange={setFillPolicy}>
  <SelectTrigger>
    <SelectValue placeholder="Fill Policy" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="optimistic">Optimistic (chạm là fill)</SelectItem>
    <SelectItem value="neutral">Neutral (có filter)</SelectItem>
    <SelectItem value="strict">Strict (khắt khe nhất)</SelectItem>
  </SelectContent>
</Select>

// Advanced Settings Collapsible
<Collapsible>
  <Switch
    checked={enableSetupTrigger}
    onCheckedChange={setEnableSetupTrigger}
  />
  <Label>Enable Setup-Trigger Model</Label>
</Collapsible>
```

### 2. Backtest List Flow

#### Backend Changes

**File: `backend/src/trading/application/backtesting/schemas.py`**

Update `BacktestRunResponse` với fields mới:
```python
class BacktestRunResponse(BaseModel):
    # ... existing fields ...
    
    # NEW: Multi-timeframe info
    data_timeframe: str
    signal_timeframe: str
    fill_policy: FillPolicy
    
    # NEW: Event counts (for debugging)
    total_htf_candles: Optional[int] = None
    total_setup_confirmed: Optional[int] = None
    total_trigger_hits: Optional[int] = None
```

#### Frontend Changes

**File: `frontend/src/pages/Backtest.tsx`**

Thêm columns vào backtest history table:
```tsx
// Add to BacktestItem interface
interface BacktestItem {
  // ... existing fields ...
  dataTimeframe: string;
  signalTimeframe: string;
  fillPolicy: 'optimistic' | 'neutral' | 'strict';
}

// Add table columns
<TableHead>
  <Button variant="ghost" onClick={() => handleSort('signalTimeframe')}>
    Signal TF <SortIcon field="signalTimeframe" />
  </Button>
</TableHead>
<TableHead>Fill Policy</TableHead>

// Add table cells
<TableCell>{backtest.signalTimeframe}</TableCell>
<TableCell>
  <Badge variant={
    backtest.fillPolicy === 'optimistic' ? 'default' :
    backtest.fillPolicy === 'neutral' ? 'secondary' : 'destructive'
  }>
    {backtest.fillPolicy}
  </Badge>
</TableCell>
```

### 3. Backtest Results/Detail Flow

#### Backend Changes

**File: `backend/src/trading/domain/backtesting/entities.py`**

Update `BacktestTrade` với missing fields:
```python
@dataclass
class BacktestTrade:
    # ... existing fields ...
    
    # NEW: Spec required fields
    signal_time: Optional[datetime] = None  # HTF close time
    execution_delay_seconds: Optional[float] = None  # entry_time - signal_time
    
    # NEW: Intra-trade metrics
    max_drawdown: Decimal = Decimal("0")  # MDD trong trade
    max_runup: Decimal = Decimal("0")     # Max unrealized profit
    
    # NEW: Fill metadata
    fill_policy_used: Optional[str] = None
    fill_conditions_met: Optional[Dict[str, bool]] = None  # Debug info
    
    # NEW: Setup-Trigger info (if enabled)
    setup_candle_time: Optional[datetime] = None
    trigger_candle_time: Optional[datetime] = None
    trigger_type: Optional[str] = None  # "limit_touch", "break_structure", etc.
```

**File: `backend/src/trading/application/backtesting/schemas.py`**

Update `TradeResponse`:
```python
class TradeResponse(BaseModel):
    # ... existing fields ...
    
    # NEW: Timeline info
    signal_time: Optional[str] = None
    execution_delay_seconds: Optional[float] = None
    
    # NEW: Intra-trade metrics
    max_drawdown: Optional[Decimal] = None
    max_runup: Optional[Decimal] = None
    
    # NEW: Fill metadata
    fill_policy_used: Optional[str] = None
    fill_conditions_met: Optional[Dict[str, bool]] = None
    
    # NEW: Reason details
    exit_reason: Optional[Dict[str, Any]] = None  # Already exists as Dict
```

**File: `backend/src/trading/presentation/controllers/backtest_controller.py`**

Thêm endpoint mới cho Event Logs:
```python
@router.get("/{backtest_id}/events", response_model=BacktestEventsResponse)
async def get_backtest_events(
    backtest_id: UUID,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Get event log for backtest debugging.
    
    Returns all events: HTF_CANDLE_CLOSED, SETUP_CONFIRMED, 
    TRIGGER_HIT, ORDER_FILLED, TP_HIT, SL_HIT, etc.
    """
    # Implementation
```

Thêm endpoint Trade Replay:
```python
@router.get("/{backtest_id}/trades/{trade_id}/replay", response_model=TradeReplayResponse)
async def replay_trade(
    backtest_id: UUID,
    trade_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    repository: BacktestRepository = Depends(get_backtest_repository),
):
    """
    Replay a specific trade with full candle-by-candle detail.
    
    Returns all candles, signals, triggers, and decisions made during this trade.
    """
    # Implementation
```

#### Frontend Changes

**File: `frontend/src/pages/BacktestDetail.tsx`**

Thêm Enhanced Trade Table với fields mới:
```tsx
interface Trade {
  // ... existing fields ...
  signal_time?: string;
  execution_delay_seconds?: number;
  max_drawdown?: number;
  max_runup?: number;
  fill_policy_used?: string;
  exit_reason?: Record<string, any>;
}

// Enhanced Trade Table Columns
<TableHead>Signal Time</TableHead>
<TableHead>Entry Time</TableHead>
<TableHead>Delay</TableHead>
<TableHead>Max DD</TableHead>
<TableHead>Max Runup</TableHead>
<TableHead>Exit Reason</TableHead>

// Table Cells with formatting
<TableCell>
  {trade.signal_time ? formatDateTime(trade.signal_time) : '-'}
</TableCell>
<TableCell>
  {formatDateTime(trade.entry_time)}
</TableCell>
<TableCell>
  {trade.execution_delay_seconds ? 
    `${trade.execution_delay_seconds}s` : '-'}
</TableCell>
<TableCell className={trade.max_drawdown && trade.max_drawdown < 0 ? 'text-red-500' : ''}>
  {trade.max_drawdown?.toFixed(2)}%
</TableCell>
<TableCell className="text-green-500">
  {trade.max_runup?.toFixed(2)}%
</TableCell>
<TableCell>
  <Badge variant="outline">
    {trade.exit_reason?.reason || 'Unknown'}
  </Badge>
</TableCell>
```

Thêm Event Log Tab:
```tsx
// New Tab in BacktestDetail
<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="trades">Trades</TabsTrigger>
    <TabsTrigger value="events">Event Log</TabsTrigger> {/* NEW */}
    <TabsTrigger value="equity">Equity Curve</TabsTrigger>
  </TabsList>
  
  <TabsContent value="events">
    <EventLogTable backtestId={id} />
  </TabsContent>
</Tabs>
```

Thêm Trade Replay Dialog:
```tsx
// Trade Replay Button in Trade Table
<Button 
  variant="ghost" 
  size="sm"
  onClick={() => openTradeReplay(trade.trade_id)}
>
  <PlayCircle className="h-4 w-4" />
  Replay
</Button>

// Trade Replay Dialog Component
<Dialog open={replayDialogOpen}>
  <DialogContent className="max-w-4xl">
    <DialogHeader>
      <DialogTitle>Trade Replay - {selectedTrade?.trade_id}</DialogTitle>
    </DialogHeader>
    
    {/* Timeline visualization */}
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge>HTF Close: {replayData?.signal_time}</Badge>
        <ArrowRight />
        <Badge variant="secondary">Setup Confirmed</Badge>
        <ArrowRight />
        <Badge variant="secondary">Trigger Hit: {replayData?.trigger_time}</Badge>
        <ArrowRight />
        <Badge variant="success">Entry: {replayData?.entry_time}</Badge>
      </div>
      
      {/* Candle-by-candle playback */}
      <CandleReplayVisualization data={replayData?.candles} />
      
      {/* Decision log */}
      <Card>
        <CardHeader>Fill Conditions</CardHeader>
        <CardContent>
          {replayData?.fill_conditions_met && 
            Object.entries(replayData.fill_conditions_met).map(([key, met]) => (
              <div key={key} className="flex items-center gap-2">
                {met ? <CheckCircle className="text-green-500" /> : <XCircle className="text-red-500" />}
                <span>{key}</span>
              </div>
            ))
          }
        </CardContent>
      </Card>
    </div>
  </DialogContent>
</Dialog>
```

### 4. New Components Needed

**File: `frontend/src/components/backtest/EventLogTable.tsx` (NEW)**
```tsx
// Component to display event logs
export function EventLogTable({ backtestId }: { backtestId: string }) {
  // Fetch events from GET /backtests/{id}/events
  // Display table with: timestamp, event_type, details
}
```

**File: `frontend/src/components/backtest/CandleReplayVisualization.tsx` (NEW)**
```tsx
// Component to visualize candle-by-candle replay
export function CandleReplayVisualization({ data }: { data: any[] }) {
  // Interactive timeline slider
  // Candle chart showing price movement
  // Highlight entry/exit points
}
```

**File: `frontend/src/components/backtest/FillPolicyBadge.tsx` (NEW)**
```tsx
// Reusable badge for fill policy display
export function FillPolicyBadge({ policy }: { policy: string }) {
  // Color-coded badge based on policy strictness
}
```

### 5. Database Schema Changes

**File: `backend/alembic/versions/xxx_add_spec_fields.py` (NEW Migration)**
```python
# Add columns to backtest_trades table
op.add_column('backtest_trades', sa.Column('signal_time', sa.DateTime(), nullable=True))
op.add_column('backtest_trades', sa.Column('execution_delay_seconds', sa.Float(), nullable=True))
op.add_column('backtest_trades', sa.Column('max_drawdown', sa.Numeric(), nullable=True))
op.add_column('backtest_trades', sa.Column('max_runup', sa.Numeric(), nullable=True))
op.add_column('backtest_trades', sa.Column('fill_policy_used', sa.String(), nullable=True))
op.add_column('backtest_trades', sa.Column('fill_conditions_met', sa.JSON(), nullable=True))

# Add columns to backtest_runs table
op.add_column('backtest_runs', sa.Column('data_timeframe', sa.String(), nullable=True))
op.add_column('backtest_runs', sa.Column('signal_timeframe', sa.String(), nullable=True))
op.add_column('backtest_runs', sa.Column('fill_policy', sa.String(), nullable=True))

# Create backtest_events table (NEW)
op.create_table('backtest_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('backtest_id', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['backtest_id'], ['backtest_runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
)
```



**Phase 1 - Critical (Foundation):**
1. Multi-timeframe Core: Resample 1m → HTF, emit HTF_CANDLE_CLOSED event.
2. Fill Policy Configuration: Thêm enum FillPolicy và implement Neutral/Strict mode.
3. Gap Detection: Check open price trước khi fill limit orders.

**Phase 2 - High Priority (Accuracy):**
4. Price Path Assumption: Config cho TP/SL conflict.
5. Enhanced Trade Records: Thêm missing fields (`signal_time`, `execution_delay`, `max_drawdown`, `runup`).
6. Event Architecture: Implement event emitter pattern.

**Phase 3 - Nice to Have (Advanced Features):**
7. Setup-Trigger State Machine: Auto-pending và scan trigger.
8. Grid/DCA Auto-Management: Thứ tự fill logic.
9. Margin Validation: Pre-fill capital check.
10. Trade Replay: Snapshot & replay mechanism.
