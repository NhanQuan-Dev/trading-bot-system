# Debugging Experience & Common Bug Patterns

> Documentation of characteristic bugs encountered during development and their solutions for faster future debugging.

---

## 🔴 Frontend React Crashes

### Pattern 1: Black Screen on Page Load (Delayed Crash)

**Symptoms:**
- Page loads briefly showing data
- Then crashes to black screen
- Console shows React error boundary message

**Common Causes:**

#### 1. Unsafe `.toFixed()` on Nullable Numbers
```typescript
// ❌ BAD - Crashes if winRate is null/undefined
{backtest.winRate !== null ? `${backtest.winRate.toFixed(1)}%` : '-'}

// ✅ GOOD - Safe with != null check (catches both null & undefined)
{backtest.winRate != null ? `${Number(backtest.winRate).toFixed(1)}%` : '-'}
```

**Why it crashes:**
- `!== null` only checks for `null`, not `undefined`
- Calling `.toFixed()` on `null` or `undefined` throws TypeError
- Crash happens AFTER data loads when rendering stats

**Fix Pattern:**
1. Use `!= null` instead of `!== null` (loose equality catches both)
2. Wrap in `Number()` before calling `.toFixed()` for extra safety
3. Always provide fallback value with ternary operator

**Related Files:** Frontend table/card rendering components

---

#### 2. Missing Status in Config Object

```typescript
// ❌ BAD - Crashes if status not in config
const config = statusConfig[backtest.status]; // undefined.icon throws error

// ✅ GOOD - Provide fallback
const config = statusConfig[backtest.status] || statusConfig['pending'];
```

**Why it crashes:**
- Backend may return new status types not defined in frontend
- Accessing `.icon` or `.label` on undefined crashes render

**Fix Pattern:**
- Add all possible backend statuses to config object
- Include common aliases (e.g., `failed`, `cancelled`, `error`)
- Always provide fallback with `||`

---

#### 3. React Anti-Pattern: `useMemo` with Side Effects

```typescript
// ❌ BAD - useMemo should NOT have side effects
useMemo(() => {
  setCurrentPage(1);
}, [searchQuery]);

// ✅ GOOD - Use useEffect for side effects
useEffect(() => {
  setCurrentPage(1);
}, [searchQuery]);
```

**Why it crashes:**
- `useMemo` is for computed values only, not side effects
- Calling setState inside `useMemo` can cause infinite render loops
- Unpredictable behavior and hard-to-debug crashes

**Fix Pattern:**
- Use `useEffect` for any setState calls
- Use `useMemo` only for expensive calculations
- Never trigger side effects in `useMemo`

---

### Pattern 2: Data Fetch & State Update Issues

#### Invalid API Response Structure

```typescript
// ❌ BAD - Assumes data.backtests exists
const mapped = data.backtests.map(...)

// ✅ GOOD - Validate before using
if (!data.backtests || !Array.isArray(data.backtests)) {
  console.error("Invalid data:", data);
  setBacktests([]);
  return;
}
const mapped = data.backtests.map(...)
```

**Debugging Approach:**
1. Add console.log at each step of async fetch
2. Validate API response structure before processing
3. Set empty array as fallback to prevent crashes

---

## 🟡 Backend Data Mapping Issues

### Pattern 3: Missing Field Mappings

**Symptom:** UI shows "N/A", "Unknown", or default values instead of real data

**Common Causes:**

#### 1. Repository Not Mapping Database Columns to Entity

```python
# ❌ BAD - Missing field mapping
BacktestRun(
    id=model.id,
    symbol=model.symbol,
    # timeframe field missing!
)

# ✅ GOOD - All fields mapped
BacktestRun(
    id=model.id,
    symbol=model.symbol,
    timeframe=model.timeframe,  # Added
)
```

**Fix Pattern:**
1. Review `_model_to_entity` method in repository
2. Ensure ALL database columns are mapped
3. Check entity dataclass for new fields that need mapping

**Related Files:** 
- `infrastructure/backtesting/repository.py`
- `domain/backtesting/entities.py`

---

#### 2. Missing Eager Loading for Relationships

```python
# ❌ BAD - Lazy loading causes N+1 queries or missing data
result = await session.execute(select(BacktestRunModel).where(...))

# ✅ GOOD - Eager load relationships
result = await session.execute(
    select(BacktestRunModel)
    .options(selectinload(BacktestRunModel.strategy))
    .where(...)
)
```

**Why it fails:**
- Without eager loading, `model.strategy` may be `None`
- Accessing `model.strategy.name` crashes or returns None

**Fix Pattern:**
- Always use `.options(selectinload(...))` for foreign key relationships
- Update both repository queries AND mapping logic

---

### Pattern 4: Incorrect Percentage Scaling

**Symptom:** UI shows 5000% instead of 50%

**Root Cause:**
```typescript
// Backend returns: win_rate = 50.00 (already a percentage)
// Frontend does: b.win_rate * 100 = 5000

// ❌ BAD
winRate: b.win_rate ? b.win_rate * 100 : null

// ✅ GOOD - API already returns percentage
winRate: b.win_rate ? b.win_rate : null
```

**Fix Pattern:**
1. Check what format backend returns (0-1 decimal vs 0-100 percentage)
2. Don't double-multiply percentages
3. Document in API schema comments

---

### Pattern 5: API Returns String Instead of Number

**Symptom:** NaN% displayed, calculations fail silently

**Root Cause:**
```typescript
// API returns: { "win_rate": "54.55" } (STRING!)
// Frontend expects number, comparison fails:
b.winRate > 0  // "54.55" > 0 is truthy but not correct numeric comparison

// ❌ BAD - No parsing
winRate: b.win_rate ? b.win_rate : null

// ✅ GOOD - Parse string to number
winRate: b.win_rate != null ? parseFloat(b.win_rate) : null
```

**Fix Pattern:**
1. Check actual API response with `curl | python3 -m json.tool`
2. Parse numeric strings with `parseFloat()` or `Number()`
3. Use `typeof value === 'number'` for type-safe filtering

**Related Files:** 
- `frontend/src/pages/Backtest.tsx` - line 145

---

### Pattern 6: ID Mapping Applied to Already-Correct UUIDs

**Symptom:** Strategy not found, wrong strategy selected, creation fails

**Root Cause:**
```typescript
// Form dropdown already uses UUID from API:
<SelectItem value={s.id}>{s.name}</SelectItem>

// ❌ BAD - Trying to map UUID through name-based lookup
const strategyId = STRATEGY_ID_MAP[strategyIdFromForm] || strategyIdFromForm;
// strategyIdFromForm = "00000000-0000-0000-0000-000000000005" (UUID)
// STRATEGY_ID_MAP["00000000-..."] = undefined → falls through

// ✅ GOOD - Use UUID directly
const strategyId = formData.get('strategy') as string;
```

**Fix Pattern:**
1. Check what value is actually in the form (name vs UUID)
2. Don't double-map - if dropdown uses ID, form field is already ID
3. Remove `STRATEGY_ID_MAP` if strategies load from API with UUIDs

---

### Pattern 7: Backend Accessing Non-Existent Model Attribute

**Symptom:** 500 error, `'ModelName' object has no attribute 'X'`

**Root Cause:**
```python
# ❌ BAD - Model doesn't have 'created_at'
"created_at": trade.created_at.isoformat(),  # AttributeError!

# Check actual model columns:
class BacktestTradeModel:
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    # No created_at!

# ✅ GOOD - Use existing attribute
"entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
```

**Debugging Approach:**
1. Check the actual SQLAlchemy model definition
2. Look for mixin inheritance (`TimestampMixin` adds `created_at`)
3. Verify which attributes exist on the specific model class

**Related Files:**
- `backend/src/trading/infrastructure/persistence/models/backtest_models.py`
- `backend/src/trading/presentation/controllers/backtest_controller.py`

---

### Pattern 8: Frontend-Backend Strategy ID Mismatch

**Symptom:** "Scalping" saves as "Momentum Strategy", wrong strategy displayed

**Root Cause:**
```typescript
// Frontend mapping:
"Scalping": "00000000-0000-0000-0000-000000000002"

// Backend seed_strategies.py:
{ "id": "...002", "name": "Momentum Strategy" }
```

**Fix Pattern - Option A (Update Backend):**
- Change `seed_strategies.py` to match frontend names

**Fix Pattern - Option B (Update Frontend) - PREFERRED:**
- Update frontend `STRATEGY_ID_MAP` and `strategyMap` to match backend
- Backend is source of truth

**Best Practice:**
- Load strategies from `/api/v1/strategies` dynamically
- Don't hardcode UUID mappings in frontend
- Use strategy.id directly from API response

---

### Pattern 9: HTML Date Input vs Backend DateTime Format

**Symptom:** 422 Unprocessable Entity when creating records

**Root Cause:**
```typescript
// HTML date input returns: "2024-01-01"
// Backend (Pydantic) expects: "2024-01-01T00:00:00"

// ❌ BAD - Raw date value
start_date: formData.get('startDate')  // "2024-01-01"

// ✅ GOOD - Convert to datetime format
start_date: `${formData.get('startDate')}T00:00:00`  // "2024-01-01T00:00:00"
```

**Debugging Approach:**
1. Check Network tab → Request payload
2. Compare with API docs expected format
3. Look for Pydantic validation errors in backend logs

**Related Files:**
- `frontend/src/pages/Backtest.tsx` - Form submission

---

### Pattern 10: Strategies API Returns Name Instead of UUID

**Symptom:** 422 error when creating backtest, payload shows `"strategy_id": "Scalping"` instead of UUID

**Root Cause:**
```json
// BAD - API returns name as ID
{"id": "Scalping", "name": "Scalping", ...}

// GOOD - API should return UUID
{"id": "00000000-0000-0000-0000-000000000005", "name": "Scalping", ...}
```

**Fix:**
```python
# In interfaces/api/v1/strategies.py
from ....infrastructure.persistence.seed_strategies import STRATEGIES

return [{"id": str(s["id"]), "name": s["name"], ...} for s in STRATEGIES]
```

**Related Files:**
- `backend/src/trading/interfaces/api/v1/strategies.py`
- `backend/src/trading/strategies/registry.py` (original issue)

---

### Pattern 11: Frontend Uses Wrong Query Parameter Names

**Symptom:** 422 "Field required" for API calls

**Root Cause:**
```typescript
// ❌ BAD - Frontend sends wrong param names
/api/v1/market-data/candles/BTC-USDT?timeframe=1h&start_date=2024-01-01

// ✅ GOOD - Match backend expectations
/api/v1/market-data/candles/BTC-USDT?interval=1h&start_time=2024-01-01T00:00:00
```

**Debugging:**
1. Check backend endpoint parameter definitions
2. Compare with frontend fetch URL
3. Match names exactly: `timeframe` → `interval`, `start_date` → `start_time`

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`
- `backend/src/trading/presentation/controllers/market_data.py`

---

### Pattern 12: Missing Field in Database Model Population

**Symptom:** Backtest stuck at 99%, SQL error with NULL value for required field

**Root Cause:**
```python
# In repository save function
result_model = BacktestResultModel(
    # ... many fields ...
    # ❌ Missing: calmar_ratio  <-- stays NULL
)

# Also missing in metrics population:
if metrics:
    result_model.sharpe_ratio = metrics.sharpe_ratio
    # ❌ Missing: result_model.calmar_ratio = metrics.calmar_ratio
```

**Fix:**
```python
# Add to default fields:
calmar_ratio=0,

# Add to metrics population:
result_model.calmar_ratio = metrics.calmar_ratio or 0
```

**Related Files:**
- `backend/src/trading/infrastructure/backtesting/repository.py`

---

### Pattern 13: DECIMAL Precision Overflow in Database

**Symptom:** Backtest stuck at 99%, SQL error `NumericValueOutOfRangeError: numeric field overflow`

**Root Cause:**
```python
# Database column DECIMAL(10,4) max value: 999999.9999
# Calculated CAGR: 2.20053419833572E+26  (10^26 - way too big!)

cagr = Decimal('2.20053419833572E+26')  # Causes overflow
```

**Fix:**
```python
def _clamp_decimal(self, value, max_val=999999.9999, min_val=-999999.9999) -> Decimal:
    """Clamp decimal to prevent DECIMAL(10,4) overflow."""
    if value is None:
        return Decimal("0")
    try:
        float_val = float(value)
        if float_val != float_val or abs(float_val) == float('inf'):  # NaN/Inf
            return Decimal("0")
        clamped = max(min_val, min(max_val, float_val))
        return Decimal(str(round(clamped, 4)))
    except (ValueError, TypeError, OverflowError):
        return Decimal("0")

# Usage:
result_model.cagr = self._clamp_decimal(metrics.compound_annual_growth_rate)
result_model.win_rate = self._clamp_decimal(metrics.win_rate, max_val=99.99)  # DECIMAL(5,2)
```

**Related Files:**
- `backend/src/trading/infrastructure/backtesting/repository.py`

---

### Pattern 14: Missing Eager Loading for Related Table Metrics

**Symptom:** UI shows 0.00 or blank for Profit Factor, Max Drawdown, Sharpe Ratio despite backtest completed successfully

**Root Cause:**
```python
# BacktestRun entity doesn't have profit_factor, max_drawdown, sharpe_ratio
# These fields exist in BacktestResultModel (separate table)
# But repository only loads BacktestRunModel without result relationship

# ❌ BAD - Missing result relationship loading
result = await session.execute(
    select(BacktestRunModel)
    .options(selectinload(BacktestRunModel.strategy))
    .where(BacktestRunModel.id == backtest_id)
)

# ❌ BAD - Entity doesn't map metrics from result
return BacktestRun(
    id=model.id,
    # ... no profit_factor, max_drawdown, sharpe_ratio
)
```

**Fix:**
```python
# 1. Add fields to entity (entities.py)
@dataclass
class BacktestRun:
    # ... existing fields ...
    profit_factor: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None

# 2. Add to response schema (schemas.py)
class BacktestRunResponse(BaseModel):
    # ... existing fields ...
    profit_factor: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None

# 3. Eager load result relationship in ALL queries (repository.py)
result = await session.execute(
    select(BacktestRunModel)
    .options(selectinload(BacktestRunModel.strategy))
    .options(selectinload(BacktestRunModel.result))  # ← Add this
    .where(BacktestRunModel.id == backtest_id)
)

# 4. Map metrics from result in _model_to_entity
profit_factor = None
max_drawdown = None
sharpe_ratio = None

if model.result:
    profit_factor = model.result.profit_factor
    max_drawdown = model.result.max_drawdown
    sharpe_ratio = model.result.sharpe_ratio

return BacktestRun(
    # ... existing mappings ...
    profit_factor=profit_factor,
    max_drawdown=max_drawdown,
    sharpe_ratio=sharpe_ratio,
)
```

**Related Files:**
- `backend/src/trading/domain/backtesting/entities.py`
- `backend/src/trading/application/backtesting/schemas.py`
- `backend/src/trading/infrastructure/backtesting/repository.py`

---

### Pattern 15: Decimal Serialized as String Causes .toFixed() Crash

**Symptom:** Black screen with console error `X.toFixed is not a function`

**Root Cause:**
```typescript
// Backend Pydantic serializes Decimal fields as STRING in JSON:
// API Response: { "profit_factor": "1.85", "max_drawdown": "15.23" }
// profit_factor is "1.85" (string), not 1.85 (number)

// ❌ BAD - Calling .toFixed() on string throws TypeError
{backtest.profit_factor?.toFixed(2)}  // "1.85".toFixed is not a function

// ❌ BAD - Nullish coalescing doesn't help, still string
{(backtest.max_drawdown ?? 0).toFixed(2)}  // "15.23".toFixed crashes
```

**Fix:**
```typescript
// ✅ GOOD - Parse string to number first, handle null
{(backtest.profit_factor != null 
    ? parseFloat(String(backtest.profit_factor)) 
    : 0
).toFixed(2)}

// ✅ GOOD - Same pattern for all Decimal fields from API
{(backtest.max_drawdown != null 
    ? parseFloat(String(backtest.max_drawdown)) 
    : 0
).toFixed(2)}%

// ✅ GOOD - Already-correct pattern for win_rate
{(backtest.win_rate != null 
    ? parseFloat(String(backtest.win_rate)) 
    : 0
).toFixed(1)}%
```

**Why `parseFloat(String(value))` is safest:**
- `String()` handles both string and number types
- `parseFloat()` converts to number
- Works regardless of API serialization format
- `!= null` catches both null and undefined

**Debugging Tip:**
```typescript
// Add this to verify API types:
console.log('profit_factor type:', typeof backtest.profit_factor);
// Output: "string" ← This is the problem!
```

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`
- Any component displaying Decimal fields from Pydantic API

---

## 🔵 Debugging Methodology

### Step-by-Step Approach for React Crashes

1. **Add Debug Logging**
   ```typescript
   console.log('[DEBUG] functionName START');
   console.log('[DEBUG] Data received:', data);
   console.log('[DEBUG] functionName END');
   ```

2. **Identify Last Successful Log**
   - Crash happens AFTER last logged line
   - Check code between last log and render

3. **Check Common Culprits**
   - `.toFixed()`, `.map()`, `.filter()` on null/undefined
   - Array access with invalid index
   - Missing keys in config objects
   - Typos in property names

4. **Isolate the Component**
   - Add try-catch around suspected render blocks
   - Return early with loading state
   - Comment out sections to narrow down

### Backend Data Flow Debugging

1. **API Response Validation**
   ```bash
   curl -s http://localhost:8000/api/endpoint | python3 -m json.tool
   ```

2. **Check Repository Mapping**
   - Add print statements in `_model_to_entity`
   - Verify all fields being mapped
   - Check for None/null values

3. **Database Query Testing**
   - Use psql/sqlite to manually query
   - Verify joins and relationships
   - Check for missing foreign key data

---

## 📋 Checklist: Before Deploying UI Changes

- [ ] All nullable properties have `!= null` checks before method calls
- [ ] Config objects include all possible enum values with fallbacks
- [ ] API data validated before mapping (array checks, null checks)
- [ ] No `useMemo` used for side effects (use `useEffect`)
- [ ] `.toFixed()` calls wrapped in `Number()` with null guard
- [ ] Console logs added for async operations (fetch start/end)
- [ ] API string values parsed with `parseFloat()` if numeric
- [ ] Strategy dropdowns use UUIDs from API, not hardcoded maps

## 📋 Checklist: Before Deploying Backend Changes

- [ ] All repository `_model_to_entity` mappings include new fields
- [ ] Foreign key relationships use `selectinload()`
- [ ] API response schemas match entity structure
- [ ] Percentage values documented (0-1 vs 0-100)
- [ ] Nullable database columns handled in mapping logic
- [ ] Only access attributes that exist on the model (check mixins)
- [ ] Seed data IDs match frontend expectations

---

## 🎯 Quick Reference: Error Messages

| Error Message | Likely Cause | Fix |
|--------------|-------------|-----|
| `Cannot read properties of null (reading 'toFixed')` | Calling `.toFixed()` on null value | Add `!= null` check |
| `Cannot read properties of undefined (reading 'map')` | Array is undefined | Validate API response before mapping |
| `backtests.undefined.tofixed is not a function` | Array access with invalid index + typo | Check array bounds and method name |
| `statusConfig[...] is undefined` | Missing status in config object | Add status to config with fallback |
| Black screen with no error | React error boundary caught error | Check browser console for stack trace |
| "Unknown Strategy" in UI | Missing eager loading or field mapping | Add `selectinload()` and map field |
| Percentage showing 5000% | Double multiplication | Remove `* 100` from frontend |
| `NaN%` displayed | API returns string, not number | Use `parseFloat()` on API value |
| `'Model' object has no attribute 'X'` | Accessing non-existent column | Check model definition for actual columns |
| Wrong strategy after save | Frontend-backend ID mismatch | Sync mappings or load from API |
| 422 with `"strategy_id": "Scalping"` | API returns name as ID | Use UUID from seed_strategies |
| 422 "Field required" for `interval` | Wrong query param name | Match backend param names exactly |
| Backtest stuck at 99% | Missing field in model save (NULL) | Add field to default values and population |
| `X.toFixed is not a function` | Decimal serialized as string | Use `parseFloat(String(value))` |
| Metric shows 0.00/blank despite data | Missing eager loading for related table | Add `selectinload()` for result relationship |

---

## 📝 Lessons Learned

1. **Always validate external data** - Never trust API responses to have expected structure
2. **Defensive programming** - Check for null/undefined before calling methods
3. **Console logging is essential** - Add debug logs liberally during development
4. **React hooks matter** - Wrong hook usage (`useMemo` vs `useEffect`) causes subtle bugs
5. **Type mismatches are silent** - TypeScript can't catch runtime null access
6. **Database relationships need eager loading** - Lazy loading causes missing data
7. **Percentage formats must be consistent** - Document if values are 0-1 or 0-100
8. **Status enums change** - Keep frontend configs in sync with backend
9. **API returns strings for decimals** - JSON serializes Decimal as string, parse it
10. **Don't double-map IDs** - If dropdown uses UUID, don't look up again
11. **Check model inheritance** - `created_at` may not exist on all models
12. **Backend is source of truth** - Frontend mappings should match backend seed data
13. **Query param names must match** - `timeframe` ≠ `interval`, `start_date` ≠ `start_time`
14. **All DB fields need defaults** - Missing field in model init causes NULL/SQL error
15. **Registry vs Seed data** - Registry uses class names, seed uses UUIDs
16. **Related table metrics need eager loading** - Metrics in child tables (BacktestResult) need `selectinload()` on parent query
17. **Always use parseFloat(String(value)) for Decimal** - Pydantic Decimal → JSON string, not number
18. **Radix TabsContent unmounts children** - Use `forceMount` prop to keep charts/complex components alive
19. **Check timestamp type before calling isoformat()** - JSON stored data has string timestamps, not datetime objects
20. **SHORT position P&L must be calculated correctly** - Entry should not modify equity, only closing with net PnL should
21. **Use UTC timezone consistently across UI** - Don't mix `toLocaleTimeString()` with UTC charts; choose one timezone
22. **Sync dual charts via subscribeVisibleLogicalRangeChange** - Use lightweight-charts API to sync scroll/zoom between stacked charts
23. **Check ALL validation paths for status-based operations** - Domain entities may have BOTH `can_be_X()` check AND the actual `X()` method checking status, both must be updated for new state transitions
24. **Unwrap API response wrappers** - If API returns `{ success, message, data }`, frontend must extract `.data`
25. **Use correct HTTP methods for actions** - State change actions (start/pause/stop) use POST, not PATCH
26. **Verify routers are registered in FastAPI app** - Importing module ≠ registering router
27. **Match service code to actual DB schema** - Column names in code must match actual table columns
28. **Handle optional dependencies gracefully** - BotManager may not be initialized, catch errors

---

### Pattern 19: Bot Stuck in STARTING Status (Duplicate Validation)

**Symptom:** Bot clicked Start, got 500 error, now stuck in STARTING. Clicking Start again fails with "Cannot start bot in STARTING status".

**Root Cause:**
```python
# TWO places checking start eligibility!
# 1. can_be_started() - for the UseCase check
def can_be_started(self) -> bool:
    return self.status in [BotStatus.STOPPED, BotStatus.ERROR]  # ❌ Missing STARTING

# 2. start() method - for the actual state transition
def start(self) -> None:
    if self.status in [BotStatus.STARTING, BotStatus.ACTIVE]:  # ❌ Blocks retry!
        raise ValueError(f"Cannot start bot in {self.status} status")
```

**Fix:**
```python
# Update BOTH checks to allow STARTING for retry:
def can_be_started(self) -> bool:
    return self.status in [BotStatus.STOPPED, BotStatus.ERROR, BotStatus.STARTING]

def start(self) -> None:
    if self.status == BotStatus.ACTIVE:  # Only block truly running bots
        raise ValueError(f"Cannot start bot in {self.status} status")
    self.status = BotStatus.STARTING
    if not self.start_time:  # Only set on first start
        self.start_time = dt.now(dt_timezone.utc)
```

**Debugging Approach:**
1. curl the API directly to get exact error message
2. If "Cannot start in X status", check BOTH `can_be_X()` AND `X()` methods
3. Create standalone debug script to test UseCase directly

**Related Files:**
- `backend/src/trading/domain/bot/__init__.py`
- `backend/src/trading/application/use_cases/bot_use_cases.py`


### Pattern 16: Radix TabsContent Unmounts Children on Tab Switch

**Symptom:** Chart/component disappears when switching tabs, requires page refresh to show again

**Root Cause:**
```typescript
// Radix TabsContent unmounts children when tab is not active
<TabsContent value="equity">
  <Chart />  {/* Chart is DESTROYED when switching to another tab */}
</TabsContent>
```

**Fix:**
```typescript
// Use forceMount to keep content in DOM, hide with CSS
<TabsContent 
  value="equity" 
  forceMount 
  className={cn("space-y-4", activeTab !== 'equity' && 'hidden')}
>
  <Chart />  {/* Chart stays in DOM, just hidden */}
</TabsContent>

// Need to track active tab
const [activeTab, setActiveTab] = useState('equity');
<Tabs value={activeTab} onValueChange={setActiveTab}>
```

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`
- Any page with complex components inside tabs

---

### Pattern 17: Timestamp String Causes .isoformat() Crash

**Symptom:** API returns `'str' object has no attribute 'isoformat'`

**Root Cause:**
```python
# Data stored as JSON in database already has string timestamps
equity_curve = [{"timestamp": "2024-01-01T00:00:00", "equity": 10.0}]

# ❌ BAD - Calling .isoformat() on already-string timestamp
return {"timestamp": point.timestamp.isoformat()}  # Crashes!
```

**Fix:**
```python
# ✅ GOOD - Check type before calling method
return {
    "timestamp": point.timestamp if isinstance(point.timestamp, str) 
                 else point.timestamp.isoformat()
}
```

**Related Files:**
- `backend/src/trading/presentation/controllers/backtest_controller.py`
- Any controller returning JSON-stored timestamp data

---

### Pattern 18: SHORT Position Equity Calculation Bug

**Symptom:** Equity curve shows near-zero or negative values mid-backtest, despite positive trades

**Root Cause:**
```python
# ❌ OLD BUG - Cash flow approach breaks with SHORT positions

# Open SHORT (adds proceeds to equity)
self.equity += entry_price * quantity

# Close SHORT (subtracts cost - WRONG APPROACH)
self.equity -= exit_price * quantity  # This causes equity to go negative!
```

**Fix:**
```python
# ✅ GOOD - Don't modify equity when opening positions
# Only update equity with net P&L when closing

def _open_long_position(self, ...):
    # Create position but DON'T modify equity
    self.current_position = BacktestPosition(...)
    self.current_position.entry_commission = fill.commission

def _open_short_position(self, ...):
    # Create position but DON'T modify equity  
    self.current_position = BacktestPosition(...)
    self.current_position.entry_commission = fill.commission

def _close_position(self, ...):
    # Calculate P&L
    if direction == LONG:
        pnl = (exit_price - entry_price) * quantity
    else:  # SHORT
        pnl = (entry_price - exit_price) * quantity
    
    # Deduct all costs
    net_pnl = pnl - entry_commission - exit_commission - slippage
    
---

### Pattern 19: Timezone Mismatch in DB Models

**Symptom:** Backtest execution stuck at 92/99%, backend logs show `DataError` or `can't subtract offset-naive and offset-aware datetimes`.

**Root Cause:**
```python
# The application uses Timezone Aware UTC datetimes:
entry_time = datetime(2024, 1, 4, 1, 0, tzinfo=timezone.utc)

# But the Database Model has Naive DateTime column (default in SQLAlchemy):
class BacktestTradeModel(Base):
    entry_time = Column(DateTime)  # Naive!
    
# When saving, SQLAlchemy/AsyncPG tries to strip timezone or compare, crashing the transaction.
```

**Fix:**
```python
# Update Models to explicitely use Timezone Aware DateTime
class BacktestTradeModel(Base):
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=False)

class BacktestRunModel(Base):
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
```

**Rule for Future:**
- Always use `DateTime(timezone=True)` in SQLAlchemy models.
- Always generate datetimes with `tz=timezone.utc`.
    
    # Only now update equity
    self.equity += net_pnl
```

**Key Insight:** Equity should only change by the realized net P&L, not by cash flowing in/out during position open.

**Related Files:**
- `backend/src/trading/infrastructure/backtesting/backtest_engine.py`

---

### Pattern 19: Timezone Mismatch Between UI Components

**Symptom:** Position Log shows time 7 hours different from what appears on chart (e.g., Position at "1:00 PM" shows on chart at "7:00 AM")

**Root Cause:**
```typescript
// Position Log uses LOCAL timezone
const entryDate = new Date(trade.entry_time);
entryDate.toLocaleTimeString()  // → "8:00:00 PM" (UTC+7 Vietnam)

// Chart uses UTC timestamp directly
time: Math.floor(new Date(point.timestamp).getTime() / 1000)
// Lightweight Charts displays UTC → "1:00:00 PM"

// Database stores UTC: "2024-01-02T13:00:00"
// Position Log converts to local: 13:00 + 7 = 20:00 (8PM)
// Chart shows raw UTC: 13:00 (1PM)
// Difference: 7 hours
```

**Fix (Use UTC everywhere for consistency):**
```typescript
// Helper functions for UTC display
const formatUTCDate = (d: Date) => d.toISOString().split('T')[0];
const formatUTCTime = (d: Date) => d.toISOString().split('T')[1].substring(0, 8);

// Position Log - use UTC format
<div>{formatUTCDate(entryDate)}</div>
<div>{formatUTCTime(entryDate)} UTC</div>

// Recharts tooltip - show UTC label
<Tooltip labelFormatter={(val) => `${val} UTC`} />

// Recharts XAxis - use raw timestamp date
<XAxis tickFormatter={(val) => val.split('T')[0]} />
```

**Key Insight:** Always choose ONE timezone for display consistency. UTC is recommended because:
- Matches database storage format
- Works across different user timezones
- No conversion needed for charts

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 20: Dual Chart with Synchronized Time Scales (Lightweight Charts)

**Requirement:** Two stacked charts (e.g., Equity on top, Drawdown below) that share the same X-axis - scrolling/zooming one chart should sync to the other.

**Solution (using lightweight-charts):**

```typescript
// Create two separate charts
const equityChart = createChart(equityContainer, {
  timeScale: { visible: false },  // Hide time axis on top chart
  // ...other options
});

const drawdownChart = createChart(drawdownContainer, {
  timeScale: { visible: true },   // Show time axis only on bottom
  // ...other options
});

// Add series to each chart
const equitySeries = equityChart.addSeries(AreaSeries, { /* green */ });
const drawdownSeries = drawdownChart.addSeries(AreaSeries, { /* red */ });

// CRITICAL: Synchronize time scales
const syncTimeScales = () => {
  const equityTimeScale = equityChart.timeScale();
  const drawdownTimeScale = drawdownChart.timeScale();

  // Sync equity -> drawdown
  equityTimeScale.subscribeVisibleLogicalRangeChange((range) => {
    if (range) {
      drawdownTimeScale.setVisibleLogicalRange(range);
    }
  });

  // Sync drawdown -> equity
  drawdownTimeScale.subscribeVisibleLogicalRangeChange((range) => {
    if (range) {
      equityTimeScale.setVisibleLogicalRange(range);
    }
  });
};
syncTimeScales();
```

**Key Points:**
- Create **separate chart instances** for each area
- Use `subscribeVisibleLogicalRangeChange` to detect scroll/zoom
- Use `setVisibleLogicalRange` to sync the other chart
- Hide time axis on top chart (`visible: false`) to avoid duplication

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 21: Radix UI Select Crash on Empty Value

**Symptom:** React crashes with `A <Select.Item /> must have a value prop that is not an empty string` when opening dialog

**Root Cause:**
```typescript
// ❌ BAD - Empty string used as value
<Select defaultValue="">
  {items.length === 0 ? (
    <SelectItem value="" disabled>No items</SelectItem>
  ) : ...}
</Select>
```

**Fix:**
```typescript
// ✅ GOOD - Use placeholder value or undefined
<Select defaultValue={undefined}>
  {items.length === 0 ? (
    <SelectItem value="__empty__" disabled>No items</SelectItem>
  ) : ...}
</Select>
```

**Related Files:**
- `frontend/src/pages/Backtest.tsx`

---

### Pattern 23: Chart Divider Resize Jumps (lightweight-charts)

**Symptom:** When dragging divider to resize charts, the chart size jumps/snaps back to original size instead of smoothly resizing

**Root Cause:**
```typescript
// ❌ BAD - resizeStartHeights set to zeros instead of actual current heights
const handleResizeStart = (divider: 'candle-equity' | 'equity-drawdown', e: React.MouseEvent) => {
  e.preventDefault();
  setResizing(divider);
  resizeStartY.current = e.clientY;
  resizeStartHeights.current = { candle: 0, equity: 0, drawdown: 0 };  // ← BUG!
};

// In mousemove handler:
const deltaY = e.clientY - resizeStartY.current;
const newCandleHeight = Math.max(minHeight, resizeStartHeights.current.candle + deltaY);
// This calculates: newHeight = 0 + deltaY, causing jumps!
```

**Why it jumps:**
- When drag starts, `resizeStartHeights` is set to `{0, 0, 0}`
- Delta calculation uses 0 as base: `newHeight = 0 + deltaY`
- Chart immediately jumps to `deltaY` pixels tall (whatever mouse movement is)
- Should use actual current heights as base for smooth incremental resize

**Fix:**
```typescript
// ✅ GOOD - Store actual current heights when drag starts
const handleResizeStart = (divider: 'candle-equity' | 'equity-drawdown', e: React.MouseEvent) => {
  e.preventDefault();
  setResizing(divider);
  resizeStartY.current = e.clientY;
  resizeStartHeights.current = { 
    candle: candleHeight,      // ← Current actual height
    equity: equityHeight,       // ← Current actual height
    drawdown: drawdownHeight    // ← Current actual height
  };
};

// Now mousemove calculates correctly:
// newHeight = currentHeight + deltaY (smooth incremental resize)
```

**Debugging Tips:**
- Console.log the `resizeStartHeights` values when drag starts
- Check if delta calculation is using correct base values
- Verify state variables hold actual current dimensions

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx` (lightweight-charts implementation)
- Any component with resizable chart dividers

**Library:** lightweight-charts (TradingView's Lightweight Charts library)

---

### Pattern 22: 401 Unauthorized in Mixed-Auth Environment

**Symptom:** Some API calls work (Mock Auth) while others fail with 401 (Real Auth)

**Root Cause:**
```typescript
// Some controllers use Mock Auth (no checks), others use Real Auth (JWT)
// Native fetch doesn't send Authorization header automatically

// ❌ BAD - Missing Auth header for protected endpoint
const res = await fetch('/api/v1/protected-resource');
```

**Fix:**
```typescript
// ✅ GOOD - Explicitly add Bearer token from storage
const token = localStorage.getItem('access_token');
const headers: HeadersInit = {
  'Content-Type': 'application/json'
};
if (token) {
  headers['Authorization'] = `Bearer ${token}`;
}

const res = await fetch('/api/v1/protected-resource', { headers });
```

**Related Files:**
- `frontend/src/pages/Backtest.tsx`
- `backend/src/trading/presentation/controllers/backtest_controller.py` (Mock Auth)
- `backend/src/trading/interfaces/api/v1/exchanges.py` (Real Auth)

---

### Pattern 23: AttributeError due to Repository Convention Mismatch

**Symptom:** `AttributeError: 'Repository' object has no attribute '_session'`

**Root Cause:**
External components (like transaction decorators or base classes) expect repositories to store the database session in `self._session`, but the repository implementation used `self.session`.

**Fix:**
Rename `self.session` to `self._session` to align with project conventions.

**Related Files:**
- `backend/src/trading/infrastructure/backtesting/repository.py`

---

### Pattern 24: 403 Forbidden due to Mock vs Real Auth Conflict

**Symptom:** `403 Forbidden: Not authorized to use this exchange connection`

**Root Cause:**
Controller used Mock Auth (returning fixed UUID) while accessing resources created by Real Auth (Active User). Mismatch in IDs caused ownership check failure.

**Fix:**
1. Replace Mock Auth in controller with `get_current_active_user` dependency.
2. Ensure Frontend sends `Authorization: Bearer <token>` header in requests.

**Related Files:**
- `backend/src/trading/presentation/controllers/backtest_controller.py`
- `frontend/src/pages/Backtest.tsx`
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 25: Property Mismatch in Value Objects

**Symptom:** `AttributeError: 'APICredentials' object has no attribute 'api_secret'`

**Root Cause:**
Controller code assumed incorrect property name (`api_secret`) while the Value Object defined it as `secret_key`. This often happens when refactoring or misremembering the domain model.

**Fix:**
Verify the domain entity/value object definition and update the consumption code to match.
`api_secret` -> `secret_key`.

**Related Files:**
- `backend/src/trading/presentation/controllers/backtest_controller.py`
- `backend/src/trading/domain/exchange/__init__.py`

---

### Pattern 26: Missing Imports during Refactoring

**Symptom:** `NameError: name 'uuid' is not defined`

**Root Cause:**
When rewriting code to manually generate IDs using `uuid.uuid4()`, the `uuid` module was not imported (only `UUID` class was).

**Fix:**
Add `import uuid` to imports.

**Related Files:**
- `backend/src/trading/presentation/controllers/backtest_controller.py`

---

---

### Pattern 27: Lightweight Charts v5 Markers API Change

**Symptom:** `TypeError: candleSeries.setMarkers is not a function`

**Root Cause:**
In Lightweight Charts v5, `setMarkers` was removed from the series instance. It is now handled via a standalone function: `createSeriesMarkers`.

```typescript
// ❌ BAD - v4 API (Deprecated/Removed in v5)
candleSeries.setMarkers(markers);

// ✅ GOOD - v5 API
import { createSeriesMarkers } from 'lightweight-charts';
const markersPlugin = createSeriesMarkers(candleSeries, markers);
```

**Fix:**
Import `createSeriesMarkers` and pass the series instance and markers array to it.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 28: Drawing Connecting Lines in Lightweight Charts

**Requirement:** Connect two points (Entry → Exit) with a line on a Candle Chart.

**Solution:**
Use `LineSeries` with specific data points.
CRITICAL: `lightweight-charts` requires time to be in strictly ascending order.

```typescript
// ❌ BAD - Can crash if entryTime > exitTime (shouldn't happen in logic but possible in data error)
tradeLine.setData([
  { time: entryTime, value: entryPrice },
  { time: exitTime, value: exitPrice }
]);

// ✅ GOOD - Ensure time ascending order
const t1 = Math.min(entryTime, exitTime);
const t2 = Math.max(entryTime, exitTime);
const v1 = entryTime < exitTime ? entryPrice : exitPrice;
const v2 = entryTime < exitTime ? exitPrice : entryPrice;

tradeLine.setData([
  { time: t1, value: v1 },
  { time: t2, value: v2 }
]);
```

**Note on Styling:**
- `lineStyle: 2` = Dashed.
- Thin lines (1px) with `rgba` colors may be invisible on some monitors. Use solid hex colors keying off opacity if needed.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 29: Case-Sensitive String Comparison Logic Errors

**Symptom:** "Long" trades displayed as "SHORT" or mapped to wrong side.

**Root Cause:**
Database returns lowercase `'long'`, but frontend checks for uppercase `'LONG'`.

```typescript
// ❌ BAD - Strict case comparison
const isLong = trade.side === 'LONG'; // false if side is 'long'

// ✅ GOOD - Case-insensitive or normalized comparison
const isLong = trade.side?.toUpperCase() === 'LONG';
```

**Fix:**
Always normalize strings (e.g., toUpperCase()) before comparing enum-like string values from API.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---


---

### Pattern 30: Implicit Sort Order Assumption Mismatch

**Symptom:** Backtest trades run backwards in time (Entry > Exit), or Entry connects to Exit roughly in reverse chronological order.

**Root Cause:**
Repository query used `order_by(Timestamp.desc())` combined with `limit` (standard for getting "Recent Data").
Backtest Engine iterated through the list assuming strict chronological order (Oldest -> Newest).
Result: The engine simulated day 5, then day 4, then day 3...
- On Day 5: Entry.
- On Day 4: Exit.
- Resulting Trade: Entry(Day 5) -> Exit(Day 4). Impossible timestamp.

**Fix:**
Service layer must explicitly sort data into the expected order (Ascending) before passing to domain services (GapDetector, BacktestEngine).

```python
# ❌ BAD - Assuming repo returns ascending
db_candles = await repo.find_lateest(...) 
# Returns [Dec 31, Dec 30, Dec 29...]

# ✅ GOOD - Explicitly ensure order
db_candles = await repo.find_latest(...)
db_candles.sort(key=lambda c: c.open_time)
# Returns [Dec 29, Dec 30, Dec 31...]
```

**Related Files:**
- `backend/src/trading/infrastructure/services/market_data_service.py`
- `backend/src/trading/infrastructure/persistence/repositories/market_data_repository.py`

---


---

### Pattern 31: "Object is disposed" Error in Lightweight Charts + React

**Symptom:** Uncaught Error: Object is disposed. Often happens when switching tabs or navigating away.

**Root Cause:**
Race condition between React `useEffect` cleanup and async callbacks (`setTimeout`, `ResizeObserver`).
1. Component unmounts -> `cleanup` calls `chart.remove()`.
2. Async event (resize/timeout) fires afterwards.
3. Callback checks `ref.current` (which still holds the *disposed* chart instance).
4. Calling `ref.current.applyOptions()` throws error.

**Fix:**
Explicitly set refs to `null` in the cleanup function *before* removing the chart. This ensures subsequent checks fail safely.

```typescript
useEffect(() => {
    // ... init chart ...
    chartRef.current = chart;

    return () => {
        // ✅ GOOD - Nullify ref first
        chartRef.current = null;
        
        try { chart.remove(); } catch(e) {}
    };
}, []);

// Async handler
const handleResize = () => {
    // Now this check safely returns false if cleaned up
    if (chartRef.current) {
        chartRef.current.applyOptions(...);
    }
}
```

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---


---

### Pattern 32: Chart Disappearance on Table Pagination

**Symptom:** 
1. Charts render correctly initially, but if user paginates a related table (Position Log), charts disappear or fail to re-render when switching tabs.
2. Connecting lines or markers "disappear" because they depended on the paginated state (which became empty or irrelevant to the chart) instead of the full dataset.

**Root Cause:**
Coupled State Dependencies.
1. The Chart `useEffect` depended on `trades` state.
2. The Table also used `trades` state, which was updated via Pagination API (e.g., getting only 20 rows).
3. Pagination update -> `trades` changes -> Chart `useEffect` cleanup runs (Destroy Chart).
4. Chart `useEffect` setup runs (Create Chart).
5. If the Chart Container is hidden (e.g., in a background Tab), initialization fails or dimensions are 0x0.
6. Also, usage of paginated data for the chart is semantically wrong (Chart should show full history, not just Page 2).

**Fix:**
Decouple the data sources.
- `allTrades`: Full history for Chart (fetched once).
- `paginatedTrades`: Subset for Table (fetched per page).

Chart `useEffect` relies on `allTrades`, so it remains stable during Table pagination.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 33: Client-Side Sorting with Backend-Paginated Data

**Symptom:** User clicks column header to sort, but sorting only applies to the current page (e.g., 20 rows) instead of the entire dataset. When sorting "P&L highest to lowest", the top result is only the max of the current page, not the global maximum.

**Root Cause:**
Backend pagination returns only N rows per page. The client stores only those N rows in state. Sorting on the client only affects those N rows, not the full dataset on the server.

```
User sees Page 1 (20 trades)
↓ Clicks "Sort by P&L Descending"
↓ Frontend sorts only those 20 trades
↓ Shows max P&L of page 1, NOT global max
```

**Fix Options:**

1. **Server-side sorting** - Pass sort parameters to API, let backend handle sorting before pagination.
   ```
   GET /trades?page=1&limit=20&sort=pnl&order=desc
   ```

2. **Client-side full dataset** (Chosen approach) - Fetch ALL data once, sort and paginate entirely on frontend.
   ```typescript
   // Fetch ALL trades once
   const allTrades = await fetchAllTrades(); // Smart pagination loop
   
   // Sort on client
   const sortedTrades = useMemo(() => 
     [...allTrades].sort((a, b) => sortFn(a, b, column, direction))
   , [allTrades, sortColumn, sortDirection]);
   
   // Frontend-only pagination
   const paginatedTrades = sortedTrades.slice(
     (page - 1) * pageSize, 
     page * pageSize
   );
   ```

**Trade-offs:**
- Option 1: More scalable for huge datasets, adds complexity to API.
- Option 2: Simpler, works well for datasets <10,000 rows. Entire dataset loaded in memory.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 34: API Limit Constraints Causing "Missing Data" Bugs

**Symptom:** 
Developers set a high `limit` (e.g., `10000`) on a GET request to fetch "all" data, but the response returns `422 Unprocessable Entity` or `400 Bad Request`.
Consequently, the frontend receives no data (or empty array), leading to **Missing Markers**, **Blank Charts**, or **Empty Lists**, even though the logic seems correct.

**Root Cause:**
Backend frameworks (FastAPI/Pydantic) often have validation rules on query parameters.
Example: `limit: int = Query(100, le=500)`
If you request `limit=10000`, the validation fails before the function executes, returning a 422 error which might be swallowed by generic error handling blocks or logged only as a warning.

**Fix:**
1. **Check Backend Constraints:** Look at the API definition for `le=` (less or equal) or `max` constraints.
2. **Increase Backend Limit:** If safe, increase the limit in the backend code (e.g., `le=10000`).
3. **Use Pagination Loop (See Pattern 35):** Instead of one giant request, use a loop to fetch correctly sized chunks.

**Related Files:**
- `backend/src/trading/presentation/controllers/backtest_controller.py`

---

### Pattern 35: Smart Pagination (Fetch-All Pattern)

**Problem:** How to fetch an **Unlimited** number of records (e.g., 50,000 trades) without hitting API timeouts or Limit constraints (Profile 34).

**Solution:** Implement a client-side "Smart Pagination" loop that automatically follows the pagination metadata until all data is retrieved.

**Implementation:**
```typescript
const PAGE_SIZE = 100; // Safe size to avoid timeouts/limits
let allRawTrades: any[] = [];
let currentPage = 1;
let totalPages = 1;

// Loop until we have fetched all pages
do {
  const res = await fetch(`/api/trades?page=${currentPage}&limit=${PAGE_SIZE}`);
  if (!res.ok) break;
  
  const data = await res.json();
  const items = data.trades || [];
  allRawTrades = [...allRawTrades, ...items];
  
  // Update totalPages from backend metadata
  if (data.pagination) {
    totalPages = data.pagination.pages;
    console.log(`Fetched page ${currentPage}/${totalPages}`);
  }
  
  currentPage++;
} while (currentPage <= totalPages);

console.log(`Total fetched: ${allRawTrades.length}`);
```

**Benefits:**
- **Robustness:** Works regardless of dataset size (100 vs 1M).
- **Compliance:** Respects backend API limits (e.g., max 500 per call).
- **Progress Visibility:** Can show progress bars (Loaded 20%...).

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 36: Undefined Variable Causing Black Screen (Refactoring Regression)

**Symptom:**
After refactoring a component (e.g., renaming a state variable), the page renders a complete "Black Screen" or blank white page.
Console shows: `Uncaught ReferenceError: x is not defined`.

**Root Cause:**
When a React component throws an error during the **render phase** (rendering JSX or executing the function body), the entire component tree unmounts if there is no Error Boundary.
In this case, `equityCurve` was renamed to `rawEquityCurve`, but the chart rendering logic still referenced `equityCurve.map(...)`.
TypeScript might miss this if:
1. `any` types are used.
2. The variable exists in a different scope (e.g., global or imported) but is not the one intended.
3. IDE refactoring tools didn't catch all usages (e.g., inside complex hooks).

**Fix:**
- Search and replace all instances of the old variable name.
- Use explicit types to help the compiler catch missing references.
- Implement an **Error Boundary** to catch render errors and show a fallback UI instead of crashing the whole app.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 37: Chart Desynchronization (Time Mismatch)

**Symptom:**
Two charts (e.g., Candles & Equity) are linked via `subscribeVisibleLogicalRangeChange` to sync crosshairs.
However, the crosshair points to "Friday" on Chart A but "Tuesday" on Chart B, despite moving perfectly in sync horizontally.

**Root Cause:**
Lightweight Charts sync based on the **Logical Index** (index 0, 1, 2...), not the Time value.
- Chart A has 1000 points (hourly candles).
- Chart B has 50 points (sparse trade events).
Index 500 on Chart A is "Date X". Index 25 on Chart B is "Date Y". They do not align.

**Fix:**
**Data Alignment (Zero-Order Hold):**
Resample Chart B to have the exact same timestamps as Chart A.
For every timestamp in Chart A:
- Find the latest known value of B.
- Create a data point for B at that timestamp.
Result: Both charts have 1000 points with identical timestamps. Sync works perfectly.

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx` (Logic: `alignedEquityCurve`)

---

### Pattern 38: Chart Visual Misalignment (Axis Width)

**Symptom:**
Multiple stacked charts share a time axis. The right edge of the plot area (canvas) is not aligned verticaly.
Crosshair behaves correctly, but the grid lines of the top chart don't line up with the bottom chart.

**Root Cause:**
Lightweight Charts automatically calculates the width of the Price Scale (Y-axis) based on the length of the labels.
- Top Chart: Label "60000.00" (Longer) -> Axis width 60px.
- Bottom Chart: Label "-1.5%" (Shorter) -> Axis width 40px.
Since the total width is fixed, the Plot Area (Canvas) shifts to fill the remaining space, causing misalignment.

**Fix:**
Enforce a **Fixed Minimum Width** for the Price Scale on all charts.
```javascript
rightPriceScale: {
    minimumWidth: 70, // Fixed width for alignment
    visible: true,
}
```

**Related Files:**
- `frontend/src/pages/BacktestDetail.tsx`

---

### Pattern 39: Multi-Layer Default Limit Causing Data Loss

**Symptom:**
Backtest runs successfully but:
1. Charts show only partial data (e.g., last 10 days instead of 60 days)
2. First trade appears much later than expected (Feb 14 instead of Jan 1)
3. Frontend market data API returns all 5,700 candles correctly
4. Database contains all 5,700 candles
5. But backtest only processes 1,500 candles

**Root Cause:**
**Multi-layer default limits** where each layer has a different default:
1. **API Controller:** `le=1000` validation (capped at 1000)
2. **Use Case:** No limit parameter passed → uses service default
3. **Service:** `limit: int = 1500` (default 1500)
4. **Repository:** Called with service's limit

When backtest use case calls service **without limit parameter**, it gets default 1500.
Service returns **last 1500 candles** from date range, ignoring earlier data.

**Timeline of Bug:**
```
Database: 5,733 candles (Jan 1 - May 1)
         ↓
Service Default: limit=1500
         ↓
Returns: Last 1500 candles = Feb 14 - May 1
         ↓
Backtest: First trade on Feb 14 (missing 4,233 candles!)
```

**Debug Process:**

1. **Frontend Check:** Verified charts fetch full data via API ✓
2. **Database Check:** Verified 5,700+ candles exist ✓
3. **Assumption:** Backend API works → Backtest must use different code path ✓
4. **Discovery:** Found `RunBacktestUseCase` calls service without `limit` parameter
5. **Service Investigation:** Found default `limit=1500` in method signature
6. **Repository Check:** Found another hardcoded `limit=1000` in `get_ohlc_data`

**The Fix Chain:**

```python
# 1. Use Case - Add explicit limit=None for backtests
# File: application/backtesting/use_cases.py:85
candles = await self.market_data_service.get_historical_candles(
    symbol=symbol,
    timeframe=timeframe,
    start_date=start_date,
    end_date=end_date,
    limit=None,  # ✅ CRITICAL FIX: Fetch ALL candles
)

# 2. Service - Change default from 1500 to Optional[None]
# File: infrastructure/services/market_data_service.py:59
async def get_historical_candles_domain(
    self,
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    limit: Optional[int] = None,  # ✅ Was: int = 1500
    repair: bool = False
) -> List[Candle]:

# 3. Repository - Pass limit through to DB query
# File: infrastructure/persistence/repositories/market_data_repository.py:326
candles = await self.find_by_symbol_and_interval(
    symbol=symbol,
    interval=interval,
    start_time=start_time,
    end_time=end_time,
    limit=None  # ✅ Was: limit=1000 hardcoded
)

# 4. Repository Method - Handle None limit (no SQL LIMIT clause)
# File: infrastructure/persistence/repositories/market_data_repository.py:268
stmt = stmt.order_by(MarketPriceModel.timestamp.desc())
if limit is not None:  # ✅ Only apply LIMIT if specified
    stmt = stmt.limit(limit)
```

**Prevention Strategy:**

**📋 Limit Audit Checklist:**
When adding time-series or historical data fetching:

1. **Service Layer:**
   ```python
   # ❌ BAD - Default limit can cause data loss
   async def get_data(symbol: str, start: Date, end: Date, limit: int = 1000):
   
   # ✅ GOOD - Require explicit limit or None
   async def get_data(symbol: str, start: Date, end: Date, limit: Optional[int] = None):
   ```

2. **Use Case Layer:**
   ```python
   # ❌ BAD - Relies on service default
   data = await service.get_data(symbol, start, end)
   
   # ✅ GOOD - Explicit limit for use case intent
   data = await service.get_data(symbol, start, end, limit=None)  # All data
   # OR
   data = await service.get_data(symbol, start, end, limit=100)  # Intentional limit
   ```

3. **API Controller:**
   ```python
   # ❌ BAD - Conservative limit blocks legitimate requests
   limit: Optional[int] = Query(None, ge=1, le=1000)
   
   # ✅ GOOD - Higher limit or no limit for internal tools
   limit: Optional[int] = Query(None, ge=1)  # No upper bound
   # OR for public APIs:
   limit: Optional[int] = Query(None, ge=1, le=100000)  # Generous limit
   ```

4. **Repository Layer:**
   ```python
   # ❌ BAD - Query applies limit even when None passed
   stmt = stmt.limit(limit or 1000)
   
   # ✅ GOOD - Only limit when explicitly requested
   if limit is not None:
       stmt = stmt.limit(limit)
   ```

**Testing Checklist:**

After fixing:
- [ ] Backtest with >2000 candles (test 60+ day range on 15m timeframe)
- [ ] Verify first trade aligns with strategy warmup (not arbitrary cutoff)
- [ ] Check equity curve starts from beginning of date range
- [ ] Request >1000 candles via API (if limit was adjusted)
- [ ] Export backtest with >10,000 trades (if export was fixed)

**Related Patterns:**
- **Pattern 34:** API Limit Constraints (validation `le=` constraints)
- **Pattern 35:** Smart Pagination (client-side pagination for large datasets)

**Related Files:**
- `application/backtesting/use_cases.py` (Backtest execution)
- `infrastructure/services/market_data_service.py` (Service layer)
- `infrastructure/persistence/repositories/market_data_repository.py` (Data access)
- `application/use_cases/market_data_use_cases.py` (Smart limit calculation)

**Security Note:**
After this fix, created comprehensive **Limit Audit Report** (`limit_audit_report.md`) documenting all 47 limit occurrences in codebase with risk classification.

**Key Lesson:**
When working with time-series data, **default limits are dangerous**. Always:
1. Make limits **explicit** (don't hide in defaults)
2. Trace through **all layers** (use case → service → repository)
3. Test with **realistic data volumes** (1000s of records, not 10s)
4. Document **why limits exist** (pagination vs business logic vs performance)

---

**Last Updated:** 2025-12-23  
**Contributors:** Development Team

---

### Pattern 35: Large Data Fetch Timeout (Chunked Job Solution)

**Symptom:** Backtest with large date range (e.g., 2 years of 15m candles = ~70K candles) times out. Job runs for 300s then fails.

**Root Cause:**
```python
# ❌ BAD - One job tries to fetch entire range
# 70,000 candles at 500/request = 140 API calls = ~5 minutes = TIMEOUT
async def execute(self, params):
    chunks = split_into_chunks(start_time, end_time)  # Creates 140 chunks
    for chunk in chunks:  # Takes 5+ minutes
        await fetch_and_save(chunk)  # Job times out before completing
```

**Fix - Sequential Chunked Jobs:**
```python
# ✅ GOOD - Each job fetches ONE chunk (1500 candles), then queues next job

# MarketDataService - queue first chunk only
chunk_duration = timedelta(minutes=interval_minutes * 1500)  # Binance max
first_chunk_end = min(gap_start + chunk_duration, gap_end)

await job_queue.enqueue(
    name='fetch_missing_candles',
    args={
        'chunk_start': gap_start.isoformat(),
        'chunk_end': first_chunk_end.isoformat(),
        'total_end': gap_end.isoformat(),
        'chunk_number': 1
    }
)

# Job - fetch chunk, queue next if needed
async def execute(self, params):
    candles = await fetch_chunk(chunk_start, chunk_end)
    await save_to_db(candles)
    
    if actual_end < total_end:
        # Queue NEXT chunk job
        await job_queue.enqueue(
            name='fetch_missing_candles',
            args={
                'chunk_start': actual_end.isoformat(),
                'chunk_end': next_chunk_end.isoformat(),
                'total_end': total_end.isoformat(),
                'chunk_number': chunk_number + 1
            }
        )
```

**Better - Parallel Chunked Jobs:**
```python
# ✅✅ BEST - Queue ALL jobs upfront, let WorkerPool handle concurrency

# MarketDataService - calculate and queue all chunks at once
chunks = []
current_start = gap_start
while current_start < gap_end:
    current_end = min(current_start + chunk_duration, gap_end)
    chunks.append({'start': current_start, 'end': current_end})
    current_start = current_end

# Queue ALL jobs
for i, chunk in enumerate(chunks):
    await job_queue.enqueue(
        name='fetch_missing_candles',
        args={
            'chunk_start': chunk['start'].isoformat(),
            'chunk_end': chunk['end'].isoformat(),
            'total_end': gap_end.isoformat(),
            'chunk_number': i + 1,
            'parallel_mode': True  # Flag to skip sequential job queuing
        }
    )

# Job - skip queueing next job when in parallel mode
if params.get('parallel_mode', False):
    return {'status': 'completed'}  # Don't queue next job
```

**Related Files:**
- `infrastructure/jobs/fetch_missing_candles_job.py`
- `infrastructure/services/market_data_service.py`

---

### Pattern 36: Dynamic Worker Pool Based on API Rate Limits

**Symptom:** Parallel jobs run too slowly (only 3 at a time) despite having 47 jobs queued.

**Root Cause:**
```python
# ❌ BAD - Hardcoded low worker count
worker_pool = WorkerPool(num_workers=3)  # Only 3 jobs parallel!
# 47 jobs / 3 workers = 16 batches × 3s each = 48 seconds
```

**Fix - Dynamic calculation based on rate limit:**
```python
# ✅ GOOD - Calculate workers from API rate limit
class WorkerPool:
    BINANCE_RATE_LIMIT_PER_MINUTE = 1200
    SAFETY_FACTOR = 0.7  # 30% headroom for other API calls
    
    @classmethod
    def calculate_optimal_workers(cls, rate_limit_per_minute=1200):
        # Formula: rate_per_second × safety_factor
        # 1200/min = 20/sec × 0.7 = 14 workers
        rate_per_second = rate_limit_per_minute / 60
        return max(1, min(int(rate_per_second * cls.SAFETY_FACTOR), 20))
    
    def __init__(self, num_workers=None):
        if num_workers is None:
            num_workers = self.calculate_optimal_workers()
        self.num_workers = num_workers

# Auto-calculates 14 workers for Binance
worker_pool = WorkerPool()  # 47 jobs / 14 workers = 4 batches = ~12 seconds!
```

**Related Files:**
- `infrastructure/jobs/job_worker.py` - WorkerPool class

---

### Pattern 37: Deleted Backtest Reappears (Re-creation by Background Jobs)

**Symptom:** Delete backtest → disappears from UI → reload page → backtest is back!

**Root Cause:**
```python
# ❌ BAD - repository.save() re-creates deleted record
async def save(self, backtest):
    existing = await session.get(BacktestRunModel, backtest.id)
    
    if existing:
        existing.status = backtest.status  # Update
    else:
        # THIS RE-CREATES THE DELETED RECORD!
        model = BacktestRunModel(id=backtest.id, ...)
        session.add(model)

# Timeline:
# 1. User deletes backtest (removed from DB)
# 2. Progress callback runs (backtest still in memory)
# 3. repository.save() called → existing=None → creates new record!
```

**Fix:**
```python
# ✅ GOOD - Skip save if record was deleted (not initial create)
async def save(self, backtest):
    existing = await session.get(BacktestRunModel, backtest.id)
    
    if existing:
        existing.status = backtest.status
    else:
        # Only create if status is PENDING (initial creation)
        # If status is RUNNING/COMPLETED, record was deleted - skip!
        if backtest.status != BacktestStatus.PENDING:
            logger.warning(f"Skipping save for deleted backtest {backtest.id}")
            return backtest  # Skip re-creation
        
        model = BacktestRunModel(id=backtest.id, ...)
        session.add(model)
```

**Also check use case restrictions:**
```python
# ❌ BAD - Blocking delete for running backtests
class DeleteBacktestUseCase:
    async def execute(self, backtest_id):
        if backtest.status == BacktestStatus.RUNNING:
            raise ValueError("Cannot delete running backtest")  # User can't delete!

# ✅ GOOD - Allow delete regardless of status
class DeleteBacktestUseCase:
    async def execute(self, backtest_id):
        # Removed status check - let user delete anytime
        return await repository.delete(backtest_id)
```

**Related Files:**
- `infrastructure/backtesting/repository.py` - save() method
- `application/backtesting/use_cases.py` - DeleteBacktestUseCase

---

### Pattern 38: Delete Button Not Visible (Conditional Rendering)

**Symptom:** User can't find delete button. "There's no delete option!"

**Root Cause:**
```tsx
// ❌ BAD - Delete button only visible for status='error'
{backtest.status === 'error' && (
  <Button onClick={() => handleDelete(backtest.id)}>
    <Trash2 />
  </Button>
)}
// Running backtest has NO delete button!
```

**Fix:**
```tsx
// ✅ GOOD - Delete button always visible for all statuses
{backtest.status === 'running' && (
  <Button onClick={() => handleStop(backtest.id)}>
    <Square /> {/* Stop button */}
  </Button>
)}

{/* Delete button - always available */}
<Button onClick={() => handleDelete(backtest.id)}>
  <Trash2 /> {/* Delete button - visible for ALL statuses */}
</Button>
```

**Debugging Tip:**
When user says "button not working", first check if button is even **rendered**:
1. Inspect element in browser DevTools
2. Search for the button text/icon in React components
3. Look for conditional rendering (`{condition && <Button />}`)

**Related Files:**
- `frontend/src/pages/Backtest.tsx` - Action buttons rendering


---

### Pattern 39: Large Dataset Rendering in Tables (Client-Side Pagination)

**Symptom:** Page lags or freezes when viewing "Position Log" with 10,000+ trades. Browser crashes due to DOM overload.

**Root Cause:**
```typescript
// ❌ BAD - Rendering all rows at once
{trades.map(trade => (
  <TableRow>...</TableRow>
))}
// 10,000 trades = 10,000 table rows = ~100k DOM nodes!
```

**Optimization (Implemented):**
1.  **Client-Side Pagination:** Only render a slice of data (e.g., 20 items) at a time.
2.  **Memoized Sorting:** Compute sorted data only when inputs change.

```typescript
// ✅ GOOD - Pagination + Memoization
const [page, setPage] = useState(1);
const pageSize = 20;

// 1. Sort efficiently (Memoized)
const sortedTrades = useMemo(() => {
  return [...trades].sort(...);
}, [trades, sortColumn]);

// 2. Slice for view (Pagination)
const paginatedTrades = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedTrades.slice(start, start + pageSize);
}, [sortedTrades, page]);

// 3. Render only the slice
{paginatedTrades.map(trade => (
  <TableRow>...</TableRow>
))}
```

**Why Client-Side vs Server-Side?**
- For datasets < 50k items (JSON size < 5MB), client-side is FASTER (instant sort/filter).
- Fetching 10k items takes ~200ms once.
- Pagination interaction is then 0ms (instant).
- Server-side pagination introduces latency on every page click.

**Related Files:**
- `frontend/src/components/backtest/PositionLogTable.tsx`

---

### Pattern 40: Performance Issues with Heavy JSON Columns in List Views

**Symptom:**
Loading a list of items (e.g., Backtests) is extremely slow (3.5s for 6 items) even though pagination is used.

**Root Cause:**
SQLAlchemy `selectinload` or default loading behavior fetches ALL columns, including heavy JSON columns (`equity_curve`, `trades`) which significantly increases the payload size and serialization time.
Specifically, `BacktestRunModel` has a relationship with `BacktestResultModel` which contains potentially megabytes of JSON data in `trades` and `equity_curve`. When listing backtests, we usually only need summary metrics (ROI, Win Rate), not the full trade history.

```python
# ❌ BAD - Fetches everything including heavy JSON
result = await self._session.execute(
    select(BacktestRunModel)
    .options(selectinload(BacktestRunModel.result))
    .limit(limit)
)
```

**Fix:**
Use SQLAlchemy's `defer` (Lazy Loading for specific columns) combined with `joinedload` (to load the relationship eagerly but without specific columns).

```python
# ✅ GOOD - Defer heavy columns
result = await self._session.execute(
    select(BacktestRunModel)
    .options(
        joinedload(BacktestRunModel.result)
        .defer(BacktestResultModel.equity_curve)  # Exclude heavy JSON
        .defer(BacktestResultModel.trades)        # Exclude heavy JSON
        .defer(BacktestResultModel.monthly_returns)
        .defer(BacktestResultModel.drawdowns)
    )
    .limit(limit)
)
```

**Key Insight:**
- `selectinload`: Loads relationship in a separate query (good for collections).
- `joinedload`: Loads relationship in the same query (good for 1-to-1).
- `defer`: Tells SQLAlchemy NOT to fetch this column in the SELECT statement. It will be lazy-loaded only if accessed later (which triggers a separate query, but acceptable if we don't access it in the list view).

**Related Files:**
- `backend/src/trading/infrastructure/backtesting/repository.py`

---

### Pattern 41: Frontend Action Requests Wrong HTTP Method

**Symptom:** Bot pause/start button fails with 405 Method Not Allowed.

**Root Cause:**
```typescript
// ❌ BAD - Frontend uses updateBot() which sends PATCH request
const handleToggle = () => {
  if (bot.status === 'running') {
    updateBot(bot.id, { status: 'paused' });  // PATCH /api/v1/bots/{id}
  }
};
```
Backend expects POST to `/api/v1/bots/{id}/pause`, not PATCH to `/api/v1/bots/{id}`.

**Fix:**
```typescript
// ✅ GOOD - Use dedicated action functions that call correct endpoints
const handleToggle = async () => {
  if (bot.status === 'RUNNING') {
    await pauseBot(bot.id);  // POST /api/v1/bots/{id}/pause
  } else {
    await startBot(bot.id);  // POST /api/v1/bots/{id}/start
  }
};
```

**Related Files:**
- `frontend/src/pages/BotDetail.tsx`
- `frontend/src/lib/api/bots.ts`

---

### Pattern 42: API Response Wrapper Not Unwrapped in Frontend

**Symptom:** Black screen with "Cannot read properties of undefined (reading 'name')".

**Root Cause:**
```typescript
// ❌ BAD - API returns { success, message, bot } but frontend expects bot directly
pause: async (id: string): Promise<Bot> => {
  const response = await apiClient.post(`/api/v1/bots/${id}/pause`);
  return response.data;  // Returns { success: true, bot: {...} }
};

// Store uses response as bot, causing undefined.name error
set((state) => ({
  bots: state.bots.map(b => b.id === id ? updatedBot : b)  // updatedBot has no .name
}));
```

**Fix:**
```typescript
// ✅ GOOD - Extract bot from response wrapper
pause: async (id: string): Promise<Bot> => {
  const response = await apiClient.post(`/api/v1/bots/${id}/pause`);
  return response.data.bot;  // Extract the actual bot object
};
```

**Related Files:**
- `frontend/src/lib/api/bots.ts`
- `frontend/src/lib/store.ts`

---

### Pattern 43: UseCase Duplicate Status Update Causes "Cannot start bot" Error

**Symptom:** Start bot fails with "Cannot start bot in BotStatus.RUNNING status".

**Root Cause:**
```python
# ❌ BAD - StartBotUseCase sets status to RUNNING twice
async def execute(self, user_id: UUID, bot_id: UUID) -> Bot:
    # Line 1: Set to RUNNING
    bot.status = BotStatus.RUNNING
    await self.bot_repository.save(bot)
    
    if self.bot_manager:
        # ... bot_manager logic
    else:
        # Line 2: Calls bot.start() which ALSO checks status
        bot.start()  # ❌ Throws because status is already RUNNING!
```

**Fix:**
```python
# ✅ GOOD - Only set status directly when using manager, use start() otherwise
async def execute(self, user_id: UUID, bot_id: UUID) -> Bot:
    if self.bot_manager:
        bot.status = BotStatus.RUNNING
        await self.bot_repository.save(bot)
        # ... bot_manager logic
    else:
        bot.start()  # This sets status, start_time, clears errors
        await self.bot_repository.save(bot)
```

**Related Files:**
- `backend/src/trading/application/use_cases/bot_use_cases.py`

---

### Pattern 44: Service Uses Wrong Column Names from Different Schema

**Symptom:** `/api/connections` returns 500 Internal Server Error.

**Root Cause:**
```python
# ❌ BAD - Service assumes columns that don't exist
class ConnectionService:
    async def get_all_connections(self, user_id: str):
        for conn in connections:
            masked_key = conn.api_key[-4:]  # Column doesn't exist!
            status = conn.status            # Column doesn't exist!

# Actual DB schema has different column names:
# api_key_encrypted (not api_key)
# is_active (not status)
```

**Fix:**
```python
# ✅ GOOD - Use actual column names from model/DB
for conn in connections:
    masked_key = conn.api_key_encrypted[-4:] if conn.api_key_encrypted else ""
    status = "active" if conn.is_active else "inactive"
```

**Debugging Approach:**
1. Check the SQLAlchemy model's `__tablename__` and column definitions
2. Query `information_schema.columns` to see actual DB columns
3. Align service code with actual schema

**Related Files:**
- `backend/src/application/services/connection_service.py`
- `backend/src/trading/infrastructure/persistence/models/core_models.py`

---

### Pattern 45: Router Not Registered in FastAPI App

**Symptom:** API endpoint returns 404 Not Found.

**Root Cause:**
```python
# ❌ BAD - Controller module imported but router not registered
# In app.py, the router is commented out:
# from presentation.api.v1.connection_controller import router as connection_router
# app.include_router(connection_router)  # ← Commented out!
```

**Fix:**
```python
# ✅ GOOD - Uncomment and register the router
from presentation.api.v1.connection_controller import router as connection_router
app.include_router(connection_router)
```

**Related Files:**
- `backend/src/trading/app.py`
- `backend/src/presentation/api/v1/__init__.py`

---

### Pattern 46: BotManager Not Initialized Causes 500 Error

**Symptom:** Start/Stop bot returns 500 with "BotManager not initialized. Call init_bot_manager first."

**Root Cause:**
```python
# ❌ BAD - get_bot_manager() throws if not initialized
def get_bot_manager() -> BotManager:
    if _bot_manager_instance is None:
        raise RuntimeError("BotManager not initialized")
    return _bot_manager_instance

# Controller doesn't handle this:
bot_manager = get_bot_manager()  # ❌ Crashes if not initialized
```

**Fix:**
```python
# ✅ GOOD - Handle missing manager gracefully
try:
    bot_manager = get_bot_manager()
except RuntimeError:
    bot_manager = None  # Will just update DB status without engine

use_case = StartBotUseCase(bot_repo, bot_manager)
```

**Related Files:**
- `backend/src/trading/interfaces/api/v1/bots.py`
- `backend/src/trading/application/services/bot_manager.py`

---

### Pattern 47: React Hooks Order Violation Causes Black Screen

**Symptom:** Page loads, then immediately crashes to black screen. Console shows "Rendered more hooks than during the previous render."

**Root Cause:**
```typescript
// ❌ BAD - useState AFTER conditional returns
export default function Component() {
  const [data, setData] = useState(null);
  
  if (!data) {
    return <Loading />;  // Early return BEFORE all hooks!
  }
  
  const [isToggling, setIsToggling] = useState(false);  // ← CRASH! Hook after return
  
  return <div>...</div>;
}
```

**Why it crashes:**
- React requires hooks to be called in the SAME ORDER on every render
- Early returns cause some hooks to be skipped on some renders
- React detects the mismatch and crashes

**Fix:**
```typescript
// ✅ GOOD - ALL useState at the TOP, before any returns
export default function Component() {
  const [data, setData] = useState(null);
  const [isToggling, setIsToggling] = useState(false);  // ← BEFORE early returns
  
  if (!data) {
    return <Loading />;  // OK - hooks already called
  }
  
  return <div>...</div>;
}
```

**Debugging Approach:**
1. Look for `useState`, `useEffect`, `useCallback`, etc.
2. Check if ANY are placed after conditional `return` statements
3. Move all hooks to the top of the component

**Related Files:**
- `frontend/src/pages/BotDetail.tsx`

---

### Pattern 48: WebSocketManager API Mismatch Causes Disconnect Error

**Symptom:** Console shows `TypeError: WebSocketManager.disconnect() takes 2 positional arguments but 3 were given`

**Root Cause:**
```python
# WebSocketManager actual API:
async def connect(self, websocket: WebSocket, token: str) -> Optional[str]:
    # Authenticates via token, returns connection_id
    
async def disconnect(self, connection_id: str):
    # Takes connection_id ONLY
    
# ❌ BAD - Controller passes wrong arguments:
await websocket_manager.connect(websocket, user_id)  # user_id != token
await websocket_manager.disconnect(websocket, user_id)  # Expects connection_id only!
```

**Fix Option 1 - Don't use WebSocketManager for simple endpoints:**
```python
# ✅ GOOD - Simple connection handling without manager
@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    await websocket.accept()
    
    # Handle auth ourselves
    user_id = verify_token(token) if token else f"anon_{uuid.uuid4().hex[:8]}"
    
    try:
        await websocket.send_text(json.dumps({"type": "connected"}))
        while True:
            data = await websocket.receive_text()
            # Handle messages...
    except WebSocketDisconnect:
        pass  # Connection closes automatically
```

**Fix Option 2 - Match WebSocketManager API:**
```python
# ✅ GOOD - Use manager correctly
connection_id = await websocket_manager.connect(websocket, token)  # token, not user_id
# ... later ...
await websocket_manager.disconnect(connection_id)  # connection_id only
```

**Related Files:**
- `backend/src/trading/presentation/controllers/websocket_controller.py`
- `backend/src/trading/infrastructure/websocket/websocket_manager.py`

---

### Pattern 49: Bot Toggle Race Condition Without Loading State

**Symptom:** Clicking Start/Pause rapidly causes 400 errors: "Cannot pause bot in PAUSED status"

**Root Cause:**
```typescript
// ❌ BAD - No debounce, no loading state
const handleToggle = async () => {
  if (bot.status === 'RUNNING') {
    await pauseBot(bot.id);  // User clicks again while this is pending
  } else {
    await startBot(bot.id);
  }
};
```

**Fix:**
```typescript
// ✅ GOOD - Add loading state to prevent double-click
const [isToggling, setIsToggling] = useState(false);

const handleToggle = async () => {
  if (isToggling) return;  // Block while in progress
  setIsToggling(true);
  
  try {
    if (bot.status === 'RUNNING') {
      await pauseBot(bot.id);
    } else {
      await startBot(bot.id);
    }
    // Refetch to sync state
    const refreshedBot = await getBot(bot.id);
    setBot(refreshedBot);
  } catch (error) {
    console.error('Toggle failed:', error.response?.data?.detail);
  } finally {
    setIsToggling(false);
  }
};

// Also update button:
<Button disabled={isToggling}>
  {isToggling ? 'Loading...' : (bot.status === 'RUNNING' ? 'Pause' : 'Start')}
</Button>
```

**Related Files:**
- `frontend/src/pages/BotDetail.tsx`
- `frontend/src/pages/Bots.tsx`

---

### Pattern 50: Frontend API Response Format Mismatch

**Symptom:** Console shows "Invalid response - bot data missing" after successful API call

**Root Cause:**
```typescript
// Backend returns:
{ "success": true, "message": "Bot started", "bot": {...} }

// ❌ BAD - Only handles one format
start: async (id: string) => {
  const response = await apiClient.post(`/bots/${id}/start`);
  return response.data.bot;  // Works ONLY if .bot exists
}
```

**Fix:**
```typescript
// ✅ GOOD - Handle multiple response formats
start: async (id: string) => {
  const response = await apiClient.post(`/bots/${id}/start`);
  const data = response.data;
  
  // Format 1: { bot: {...} } wrapper
  if (data.bot) return data.bot;
  
  // Format 2: Direct bot object
  if (data.id) return data;
  
  console.warn('Unexpected response format:', data);
  return data;
}
```

**Related Files:**
- `frontend/src/lib/api/bots.ts`

---

## 📋 Quick Reference: Today's Fixes

| Error | Pattern | Fix |
|-------|---------|-----|
| "Rendered more hooks than previous render" | #47 | Move useState before early returns |
| "disconnect() takes 2 arguments but 3 given" | #48 | Match WebSocketManager API signature |
| "Cannot pause bot in PAUSED status" (double-click) | #49 | Add isToggling state to prevent double-click |
| "Invalid response - bot data missing" | #50 | Handle both wrapped and direct response formats |

## 🎨 Layout Synchronization Bugs

### Pattern 1: Flexbox Content Gaps (Scroll Mismatch)

**Symptoms:**
- Two side-by-side components in a flex row (e.g., Chart vs. List).
- One has dynamic height content (List), the other tries to match it (Chart).
- **The Bug**: After scrolling or resizing, the Chart might "stick" to a taller height or fail to shrink, causing the container to remain tall even when content is short, creating empty white space gaps.

**Common Causes:**
- **Flex Child Behavior**: A flex child with `h-full` will try to fill the *container*, but if the container's height is determined by the *other* child, circular dependencies or layout trashing can occur.
- **Intrinsic Height**: Plotly (and Recharts) charts often have an intrinsic calculated height that overrides the parent's flex shrinking preference.

**Fix Pattern: Absolute Positioning Hack**
Decouple the Chart from the layout flow entirely. Let the "List" component drive the row height, and force the Chart to simply fill whatever space is left.

```tsx
// ❌ BAD - Chart participates in height calculation
<CardContent className="h-full">
  <Plot style={{ height: '100%' }} />
</CardContent>

// ✅ GOOD - Chart is removed from flow, strictly follows parent height
<CardContent className="relative min-h-[450px]">
  {/* Absolute inset-0 forces div to match CardContent exactly */}
  <div className="absolute inset-0">
    <Plot style={{ width: '100%', height: '100%' }} />
  </div>
</CardContent>
```

**Why it works:**
1.  `relative` on parent acts as the anchor.
2.  `absolute inset-0` on child pulls it to all 4 corners of the parent.
3.  The Chart no longer pushes the parent open; it only reacts to the parent's size.
4.  The sibling component (List) becomes the *sole* driver of the row's height.

### Pattern 2: Color Mismatch (Gradient vs Solid)

**Symptoms:**
- Chart elements (e.g., Candle Body vs Wick) use the "same" green/red color but look different.
- The Body appears lighter or "washed out" compared to the Wick.

**Common Causes:**
- **Opacity in Gradients**: Often we copy-paste gradients like `<stop offset="100%" stopOpacity="0.6" />`.
- **Perceptual diff**: A line (Wick) is usually rendered as a solid 1px stroke (100% opacity). If the Body fills with 60% opacity gradient (even if the color hex is identical), it blends with the dark background and shifts the perceived hue.

**Fix Pattern: Solid Fill**
If the design requirement is "Uniform Color", delete the Gradient and use direct Hex fill.

```tsx
// ❌ BAD - Gradient Opacity causes mismatch with solid Wick
fillcolor: 'url(#gradient-green)' // defined with opacity 0.6

// ✅ GOOD - Direct Solid Hex matches the Wick perfectly
increasing: {
  line: { color: '#15FF00', width: 1 },
  fillcolor: '#15FF00' // 100% Solid
}
```

---

## 🔴 Backend Repository Issues

### Pattern 20: Duplicate Method Definitions Override Correct Implementation

**Symptoms:**
- Repository method returns `None` even though data exists in database
- Debug logs added to method don't appear in output
- Manual database query confirms data exists
- Dependency injection logs show repository is instantiated correctly

**Example:**
```python
# bot_repository.py
class StrategyRepository(IStrategyRepository):
    # Line 348: Correct implementation with debug logs
    async def find_by_id(self, strategy_id: uuid.UUID) -> Optional[Strategy]:
        print("=== DEBUG LOGS ===")  # Never executes!
        # ... correct code with safe parsing
        return strategy
    
    # ... other methods ...
    
    # Line 486: DUPLICATE from merge conflict (ZOMBIE CODE)
    async def find_by_id(self, bot_id: uuid.UUID) -> Optional[Bot]:
        # Wrong signature, wrong logic
        return None  # Python uses THIS definition!
```

**Why it fails:**
- Python classes use the **LAST** definition of a method when multiple exist
- Zombie code from merge conflicts can override correct implementations
- Debug logs in first definition never execute because Python uses second definition
- Method signature might be different, causing type errors or wrong behavior

**Root Cause:**
- File corruption from incomplete merge resolution
- Copy-paste errors creating duplicate class content
- Zombie code not properly deleted after refactoring

**Diagnosis Steps:**
1. **Search for duplicate methods:**
   ```bash
   grep -n "def find_by_id" backend/src/.../bot_repository.py
   # Output shows: 162, 348, 486 (❌ Too many!)
   ```

2. **Check for class boundaries:**
   ```bash
   grep -n "class.*Repository" backend/src/.../bot_repository.py
   # Should show ONE class definition per repository
   ```

3. **Identify zombie code:**
   - Look for code after normal class end
   - Check for incomplete/invalid logic
   - Look for references to undefined variables

**Fix Pattern:**
```python
# ❌ BAD - Multiple definitions
class StrategyRepository:
    async def find_by_id(self, id): ...  # Line 348
    async def find_by_id(self, id): ...  # Line 486 ← OVERRIDES line 348!

# ✅ GOOD - Single definition per method
class StrategyRepository:
    async def find_by_id(self, id): ...  # Only one definition
```

**Solution:**
1. Identify the range of zombie code (use line numbers from grep)
2. Delete all duplicate/zombie code:
   ```python
   # Keep lines 1-N (before zombie code)
   with open('file.py', 'r') as f:
       lines = f.readlines()
   clean_lines = lines[:438]  # Keep only valid code
   clean_lines.append('\n\n__all__ = ["BotRepository", "StrategyRepository"]\n')
   with open('file.py', 'w') as f:
       f.writelines(clean_lines)
   ```
3. Verify only one method definition remains:
   ```bash
   grep -c "async def find_by_id" file.py  # Should equal number of classes
   ```
4. Clear Python bytecode cache:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
   find . -name "*.pyc" -delete
   ```
5. Restart backend completely

**Prevention:**
- Review merge conflicts carefully
- Use `git mergetool` for complex merges
- Run linters/type checkers that catch duplicate methods
- Before committing, verify:
  ```bash
  # Count method definitions
  grep -c "def method_name" file.py  # Should match expected count
  
  # Check for zombie code after class end
  # Look for code that references wrong types/undefined vars
  ```

**Related Files:**
- `backend/src/trading/infrastructure/persistence/repositories/bot_repository.py`
- Any repository file with merged changes

**Debugging Time:** 2+ hours (if not familiar with this pattern)

**Key Indicators:**
- Debug logs don't appear ✅
- Data exists in DB but query returns None ✅
- Multiple `grep` hits for same method name ✅
- File unusually long (e.g., 600+ lines for simple repo) ✅

---

## Pattern 21: Frontend API Path Mismatch (404 Not Found)

**Symptoms:**
- Frontend console shows 404 Not Found errors
- API endpoints exist in backend but return 404
- CORS errors may appear alongside (secondary effect)

**Root Cause:**
Frontend calls `/api/bots/...` but backend routes are under `/api/v1/bots/...`

**Diagnosis:**
```bash
# Check what frontend is calling
grep -r "/api/bots" frontend/src/

# Check backend route prefix
grep -r "prefix=" backend/src/trading/interfaces/api/
```

**Solution:**
```typescript
// ❌ Wrong - missing /v1
const response = await apiClient.get(`/api/bots/${botId}/positions`);

// ✅ Correct - includes API version
const response = await apiClient.get(`/api/v1/bots/${botId}/positions`);
```

**Related Files:**
- `frontend/src/pages/BotDetail.tsx`
- Any frontend component calling backend APIs

---

## Pattern 22: ImportError for Database Context Function

**Symptoms:**
- 500 Internal Server Error on API calls
- Backend logs show: `ImportError: cannot import name 'get_db_session'`

**Root Cause:**
Database module exports `get_db_context` but code imports `get_db_session` (non-existent function)

**Diagnosis:**
```bash
# Check what database module exports
grep "def get_db" backend/src/trading/infrastructure/persistence/database.py

# Find wrong imports
grep -r "get_db_session" backend/src/
```

**Solution:**
```python
# ❌ Wrong
from ...infrastructure.persistence.database import get_db_session
async with get_db_session() as session:

# ✅ Correct
from ...infrastructure.persistence.database import get_db_context
async with get_db_context() as session:
```

**Related Files:**
- `backend/src/trading/presentation/controllers/bots.py`
- Any controller using database sessions

---

## Pattern 23: WebSocket Connection Errors (Binance Testnet vs Mainnet)

**Symptoms:**
- Console shows WebSocket errors to Binance
- Market data/candles don't update in real-time
- Error type: 'error' with WebSocket target

**Root Cause:**
1. Network issues blocking WebSocket connections
2. Wrong REST API URL for testnet
3. Browser security policies blocking mixed content

**Official Binance Futures URLs:**
```
MAINNET:
  REST:      https://fapi.binance.com
  WebSocket: wss://fstream.binance.com

TESTNET:
  REST:      https://demo-fapi.binance.com
  WebSocket: wss://fstream.binancefuture.com
```

**Solution:**
```typescript
// ✅ Testnet WebSocket (correct)
const wsUrl = `wss://fstream.binancefuture.com/stream?...`;

// ✅ Testnet REST API (correct)
const url = `https://demo-fapi.binance.com/fapi/v1/klines?...`;

// ✅ Mainnet WebSocket
const wsUrl = `wss://fstream.binance.com/stream?...`;
```

**Graceful Error Handling:**
```typescript
// Use console.warn instead of console.error for expected failures
ws.onerror = (e) => {
    console.warn('[MarketData] WebSocket unavailable');
    setError('Market data stream unavailable');
    setIsConnected(false);
};
```

**Related Files:**
- `frontend/src/hooks/use-market-data.ts`
- `frontend/src/hooks/use-candle-data.ts`

---

## 🔴 Live Trading & Binance Integration Bugs

### Pattern 21: Binance Signature Verification Failed (-1022)

**Symptom:** API returns `Signature for this request is not valid`.

**Root Cause:**
```python
# ❌ BAD - Sorting parameters before signing
# Binance requires the query string to be exactly as sent, NOT sorted by key
params = sorted(params.items()) 
query_string = urllib.parse.urlencode(params)
signature = sign(query_string)
# Request sent: "a=1&b=2" (sorted)
# Signature matches "a=1&b=2"
# But validation fails if original insertion order mattered or if sorting isn't standard
```

**Fix:**
```python
# ✅ GOOD - Use parameters exactly as provided
# Use urllib.parse.urlencode() directly on the dictionary or list of tuples
query_string = urllib.parse.urlencode(params)
signature = hmac.new(..., query_string.encode('utf-8'), ...).hexdigest()
```

**Related Files:**
- `backend/src/trading/infrastructure/exchange/binance_adapter.py`

---

### Pattern 22: Hedge Mode Position Side Missing (-1117)

**Symptom:** API returns `Order's position side does not match user's setting`.

**Root Cause:**
Binance Futures in Hedge Mode requires `positionSide="LONG"` or `positionSide="SHORT"` for opening orders. Pure "BUY"/"SELL" is ambiguous between Opening Long vs Closing Short.

**Fix:**
```python
# Auto-inject positionSide based on order side (for Open actions)
if "positionSide" not in params:
    params["positionSide"] = "LONG" if side == "BUY" else "SHORT"
```

---

### Pattern 23: Minimum Notional Value Error (-4164)

**Symptom:** `Order's notional must be no smaller than 100` (Binance Testnet Rule).

**Root Cause:**
Testnet has stricter/different rules. Strategy defaulted to `0.01` BTC, but price was ~$40k. Wait, 0.01 * 40k = 400 > 100.
Actually, the error was triggered when using very small quantities like `0.001` where `0.001 * 40000 = 40 < 100`.
In this case, the `HighFrequencyTest` strategy defaulted to `0.01` in code, but the Database record had `0.002`.
`0.002 * 87000 (BTC price) = 174` (Valid).
The specific failure occurred when using defaults that calculated to < 5 USDT value in other contexts or mistakenly sending `0`.

**Fix:**
1. Ensure `strategy_config` correctly loads default parameters from Database (see Pattern 25).
2. Validate `quantity * price > 100` before sending order if on Testnet.

---

### Pattern 24: Bot Restart Failure (Stale Engine State)

**Symptom:** Bot status stuck in ERROR/STOPPED, but clicking Start says "Bot is already running".

**Root Cause:**
```python
# BotManager keeps track of running engines:
self._engines[bot_id] = engine

# When stopping, if an error processing the stop occurs, 
# the engine is NOT removed from _engines.
```

**Fix:**
```python
# In start_bot():
if bot_id_str in self._engines:
    logger.info(f"Checking if existing engine for {bot_id_str} is alive...")
    old_engine = self._engines[bot_id_str]
    # Check if actually running or just stale reference
    if not old_engine.is_running:
         del self._engines[bot_id_str]  # Cleanup stale
    else:
         return False # Truly running
```

---

### Pattern 25: Strategy Configuration & Parameter Scope

**Symptom:** Strategy ignores database parameters (e.g., `use_market_orders=False` ignored, bot keeps using `True`).

**Root Cause 1 (Merge Logic):**
`BotManager` was creating `strategy_config` using ONLY `bot.configuration`. It ignored `strategy_entity.parameters` (the defaults from the Strategy definition).

**Root Cause 2 (Nested JSON):**
Even after merging, `strategy_entity.parameters` might be deserialized as a nested dictionary or object:
```python
strategy_defaults = {'parameters': {'use_market_orders': False}}
```
The Strategy class expects `config['use_market_orders']` at the top level.

**Fix:**
```python
# 1. Merge defaults explicitly
strategy_defaults = strategy_entity.parameters or {}

# 2. Flatten nested 'parameters' key if present
if "parameters" in strategy_defaults and isinstance(strategy_defaults["parameters"], dict):
    strategy_defaults.update(strategy_defaults["parameters"])

# 3. Create final config
strategy_config = {
    **strategy_defaults,
    **bot.configuration.strategy_settings
}
```

---

### Pattern 26: Binance Limit Order Rules (TimeInForce & TickSize)

**Symptom A:** `-1102: Mandatory parameter 'timeinforce' was not sent`.
**Symptom B:** `-4014: Price not increased by tick size`.

**Root Cause:**
- **TimeInForce:** Required for LIMIT orders (e.g., `GTC`), not for MARKET.
- **Tick Size:** LIMIT price must be a multiple of tick size. BTC/USDT Futures has tick size `0.1`, but code was rounding to `0.01`.

**Fix:**
```python
# Validation in BinanceAdapter
if type == "LIMIT" and "timeInForce" not in params:
    params["timeInForce"] = "GTC"

# Rounding in Strategy
# For BTC/USDT (Generic approach needs SymbolInfo)
price = price.quantize(Decimal("0.1")) 
```

---

### Pattern 27: Database Constraint Mismatch (Enum Mapping)

**Symptom:** `IntegrityError: ... violates check constraint "ck_orders_side"`.

**Root Cause:**
- Binance returns: `BUY`, `SELL`, `NEW`, `FILLED`
- Database Constraint expects: `LONG`, `SHORT`, `PENDING`, `OPEN`

**Fix:**
Map values before modifying model:
```python
side_map = {"BUY": "LONG", "SELL": "SHORT"}
status_map = {"NEW": "PENDING", ...}

order.side = side_map.get(api_data['side'], api_data['side'])
order.status = status_map.get(api_data['status'], api_data['status'])
```

---

### Pattern 28: Registry Lookup Case Sensitivity

**Symptom:** `Strategy 'Grid Trading' not found in registry`.

**Root Cause:**
- Database Strategy Name: "Grid Trading"
- Code Class Attribute: `name = "GRID"`
- Registry uses `strategy_cls.name` as key. Lookup fails.

**Fix:**
Ensure code matches database exactly:
```python
class GridTradingStrategy(StrategyBase):
    name = "Grid Trading"  # Matches DB
```

---

### Pattern 50: 401 Invalid API Key (Encrypted String Passed as Raw)

**Symptom:** Exchange API returns 401 Unauthorized or "Invalid API Key format" even though the user entered the correct key.

**Root Cause:**
```python
# Database stores encrypted keys (e.g., "gAAAAABk...")
# Code passes this string DIRECTLY to the exchange SDK/API
client = BinanceClient(api_key=connection.api_key_encrypted, ...) 

# The exchange expects the RAW key (e.g., "vmPU..."), not the Fernet token
```

**Fix:**
```python
# ✅ GOOD - Decrypt before using
raw_key = self._decrypt(connection.api_key_encrypted)
client = BinanceClient(api_key=raw_key, ...)
```

**Debugging Approach:**
1. Print the first few characters of the key being sent (e.g., `api_key[:5]`).
2. If it starts with `gAAAA`, it's likely a Fernet token (encrypted).
3. Ensure service layer handles decryption before calling infrastructure adapters.

**Related Files:**
- `backend/src/application/services/connection_service.py`
- `backend/src/trading/infrastructure/repositories/exchange_repository.py`

---

### Pattern 51: Connection Status Icon Mismatch (Hardcoded Repository Status)

**Symptom:** User runs "Test Connection", it succeeds, but refreshing the page shows the status as "DISCONNECTED" (gray/red icon).

**Root Cause:**
```python
# Repository _to_domain method hardcodes status because DB column is missing/unused
return ExchangeConnection(
    # ...
    status=ConnectionStatus.DISCONNECTED,  # ❌ TODO: Track status in database
)
```
Updates to the object in memory during testing are lost upon next fetch because the repository forces the default value.

**Fix:**
```python
# ✅ GOOD - Infer status from other persisted flags if status column is missing
status = ConnectionStatus.CONNECTED if model.is_active else ConnectionStatus.DISCONNECTED
```

**Related Files:**
- `backend/src/trading/infrastructure/repositories/exchange_repository.py`

---

### Pattern 52: CCXT "Exchange Not Supported" in Custom Environments

**Symptom:** `ccxt.binance()` errors with "Exchange not supported" or fails key validation unexpectedly when used inside a complex app.

**Root Cause:**
- Mismatch in default configuration options (testnet vs mainnet URLs).
- CCXT constructor arguments might not match the specific headers needed for the environment.

**Fix:**
- Use a dedicated Adapter class (`BinanceAdapter`) where you have full control over URLs and authentication headers.
- Explicitly handle Testnet URL mapping logic (`fapi.binance.com` vs `testnet.binancefuture.com`).

**Related Files:**
- `backend/src/trading/infrastructure/exchange/binance_adapter.py`

---

### Pattern 53: Symbol Mismatch (Exchange vs Bot Format)

**Symptom:** API returns 200 OK, but lists (Positions, Orders) are empty on the UI when they shouldn't be.

**Root Cause:**
- Bot Configuration uses: `"BTC/USDT"` (common display format).
- Exchange API returns: `"BTCUSDT"` (raw format).
- Code string comparison fails: `"BTC/USDT" == "BTCUSDT"` is False.

**Fix:**
```python
# ✅ GOOD - Normalize before comparing
target_symbol = bot.configuration.symbol.replace("/", "").upper()
if position.symbol == target_symbol:
    # ...
```

**Related Files:**
- `backend/src/trading/application/services/position_service.py`

---

### Pattern 54: Database Model Attribute Error (Field Mismatch)

**Symptom:** `500 Internal Server Error` with `AttributeError: 'PositionModel' object has no attribute 'current_price'`.

**Root Cause:**
- Developer assumed `PositionModel` has `current_price` because the Frontend API response uses that key.
- Actual Database Column is `mark_price` or `last_price`.
- Mapping logic attempted to assign to the Model's non-existent attribute.

**Fix:**
Check `models/trading_models.py` definition.
```python
# ✅ GOOD - Map explicit columns
db_pos.mark_price = ex_pos.mark_price  # Write to DB column
...
"current_price": db_pos.mark_price     # Read for API response
```

**Related Files:**
- `backend/src/trading/infrastructure/persistence/models/trading_models.py`
- `backend/src/trading/application/services/position_service.py`

---

### Pattern 55: IntegrityError (Missing Required Foreign Keys/Fields)

**Symptom:** `500 Internal Server Error` with `NotNullViolationError` or `IntegrityError` during `INSERT`.

**Root Cause:**
- Creating a new DB entity without providing all `nullable=False` fields.
- Triggered when converting an External Object (Exchange Position) to Internal Entity (PositionModel) and forgetting relations like `user_id` or `exchange_id` that aren't present in the external data.

**Fix:**
Ensure Context (User ID, Exchange Connection ID) is passed down to the mapping function.
```python
new_pos = PositionModel(
    user_id=bot.user_id,             # Required
    exchange_id=connection.exchange_id, # Required
    ...
)
```

**Related Files:**
- `backend/src/trading/application/services/position_service.py`

---

### Pattern 56: Incorrect API Endpoint Logic (Missing Data)

**Symptom:** `KeyError: 'markPrice'` or application crash when parsing API response.

**Root Cause:**
- Developer assumed `/fapi/v2/account` returns `markPrice` for positions.
- Actually, that endpoint only returns `entryPrice` and `unrealizedProfit`. `markPrice` lives in `/fapi/v2/positionRisk`.

**Fix:**
- Verify API Schema documentation carefully.
- Aggregate data from multiple endpoints if necessary (e.g., fetch Account + PositionRisk in parallel).

**Related Files:**
- `backend/src/trading/infrastructure/exchange/binance_adapter.py`


### Pattern 57: WebSocket Connection Method Mismatch & Token Invalidation

**Symptoms:**
- WebSocket connection fails immediately with "Connection failed".
- Backend logs show no errors or don't register the attempt.
- Browser console shows `WebSocket connection to 'ws://...' failed`.

**Common Causes:**
1.  **Handler Mismatch**: Logic for handling specific message types (e.g., `start_bot_stream`) is placed in the wrong handler function (e.g., `handle_general_message` instead of `handle_websocket_message`).
2.  **Auth Token Expiry**: On backend restart, in-memory tokens or sessions might be invalidated. Frontend tries to reconnect with the old token, which is rejected during the handshake.

**Fix:**
1.  **Verify Handler Logic**: Ensure message types are handled in the correct function corresponding to the endpoint (`/ws` vs `/ws/trading`).
2.  **Refresh Auth**: If backend restarts, manually refresh the frontend page or re-login to generate a fresh JWT token. The previous token is likely invalid.

---

## 🔐 Authentication & WebSocket Debugging

### Pattern 1: Login Loop vs Library Incompatibility

**Symptom:** 
- User enters correct credentials
- Browser redirects to `/login` immediately
- No visible error in frontend (generic 401)
- Backend logs show `AttributeError: module 'bcrypt' has no attribute '__about__'` inside `passlib`

**Root Cause:**
`passlib` (v1.7.4) has a known incompatibility with newer versions of `bcrypt` (>4.0.0). Using `passlib.context.CryptContext` triggers an internal crash when trying to verify passwords.

```python
# ❌ BAD - Incompatible with newer bcrypt
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# pwd_context.verify(plain, hashed) -> CRASH
```

**Fix:**
Replace `passlib` context with direct `bcrypt` library usage.

```python
# ✅ GOOD - Direct bcrypt usage
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Ensure bytes for bcrypt
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
        
    return bcrypt.checkpw(plain_password, hashed_password)
```

**Related Files:**
- `backend/src/trading/domain/user/__init__.py`

---

### Pattern 2: WebSocket 1008/4001 Errors (The "Perfect Storm" Bug)

**Symptom:** 
- Login successful, but real-time connection rejected
- `WebSocket connection failed` with 1008 (Policy Violation) or 4001 (Unauthorized)
- Backend may crash silently or show "Expected ASGI message"

**Common Causes & Fixes:**

#### 1. Dependency Injection Failure
**Cause:** `UserRepository` initialized without a DB session in controller.
```python
# ❌ BAD
user_repository = UserRepository()  # TypeError: missing 'session' arg
```
**Fix:** Inject session via FastAPI `Depends`.
```python
# ✅ GOOD
async def endpoint(db = Depends(get_db)):
    user_repository = UserRepository(db)
```

#### 2. Protocol Violation (Double Accept)
**Cause:** Calling `await websocket.accept()` in BOTH the Controller and the Manager.
```python
# ❌ BAD - Controller accepts, then Manager accepts again
await websocket.accept()
await manager.connect(websocket)  # Inside connect: await websocket.accept()
```
**Fix:** Remove one `accept()` call (usually keep it in the Manager or Controller, but not both).

#### 3. Token vs UserID Logic Error
**Cause:** Manager expects a raw Token to decode, but Controller already decoded it.
```python
# ❌ BAD
# Controller:
user_id = verify_token(token)
manager.connect(websocket, user_id)

# Manager:
def connect(self, ws, token):
    user_id = verify_token(token) # Fails because 'token' is actually 'user_id' string
```
**Fix:** Refactor Manager to accept a validated `user_id`.

#### 4. Disconnect Signature Mismatch
**Cause:** `finally` block calls `disconnect` with wrong args.
```python
# ❌ BAD
finally:
    await manager.disconnect(websocket, user_id) # TypeError if signature is (connection_id)
```
**Fix:** Capture `connection_id` from connect and use it for disconnect.
```python
# ✅ GOOD
connection_id = await manager.connect(websocket, user_id)
try:
    ...
finally:
    await manager.disconnect(connection_id)
```

---

## 🟣 WebSocket & Real-Time Data Issues

### Pattern 20: Stubbed Methods Causing Silent Data Loss

**Symptom:** Logs show "Broadcasting..." but client receives nothing. No errors in logs.

**Root Cause:**
```python
# ❌ BAD - Stubbed method in dependency
class ConnectionManager:
    async def broadcast(self, msg):
        # TODO: Implement this
        pass  # ❌ Silent failure!
        
class WebSocketManager:
    async def send(self):
        logger.info("Broadcasting...")
        await connection_manager.broadcast(msg) # Returns None immediately
```

**Debugging Approach:**
1. Trace the *exact* execution path.
2. Don't trust "Broadcasting" logs - they only mean the *attempt* started.
3. Check the implementation of every method in the chain.

---

### Pattern 21: Cache Key Collision in Hedge Mode

**Symptom:** "Disappearing" positions. Updating one position causes another to vanish.
**Context:** Hedge Mode allows holding both LONG and SHORT positions for the same symbol (e.g., BTCUSDT).

**Root Cause:**
```python
# ❌ BAD - Using only symbol as key
cache[symbol] = position_data
# BTCUSDT (Long) -> Saved to cache["BTCUSDT"]
# BTCUSDT (Short) -> Overwrites cache["BTCUSDT"]
```

**Fix:**
```python
# ✅ GOOD - Composite key
key = f"{symbol}_{side}"  # BTCUSDT_LONG
cache[key] = position_data
```

---

### Pattern 22: Loop Indentation Logic Error

**Symptom:** Only the *last* item in a list gets updated/calculated correctly. Others have stale data.

**Root Cause:**
```python
# ❌ BAD - Calculation outside loop
for pos in positions:
    update_price(pos)

calculate_pnl(pos) # ❌ Uses loop variable 'pos' which is now the LAST item only!
```

**Fix:**
```python
# ✅ GOOD - Calculation inside loop
for pos in positions:
    update_price(pos)
    calculate_pnl(pos) # ✅ Updates every item
```

---

### Pattern 23: Incomplete API Object Mapping

**Symptom:** UI shows default value (e.g., "Cross" leverage) instead of actual value, even though API returns it.

**Root Cause:**
```python
# API returns: { "marginType": "isolated" }
# Dataclass:
class PositionData:
    symbol: str
    # ❌ margin_type missing!
    
# Adapter:
return PositionData(...) # Field dropped
```

**Fix:**
1. Update Dataclass/Entity to include the field.
2. Update Adapter mapping logic (`margin_type=data.get("marginType")`).
3. Update Service/Frontend to use the new field.

---

### Pattern 24: Real-time Update Overwriting Valid Data

**Symptom:** Data loads correctly (e.g., Leverage 13x), then resets to default (1x) after a few seconds.

**Root Cause:**
```python
# Initial Load (REST API): Returns full data (leverage=13)
# Real-time Update (WebSocket): Returns partial data (leverage MISSING)

# ❌ BAD - Defaulting to 1 if missing
leverage = event.get("l", 1) # event["l"] is None -> sets 1
```

**Fix:**
```python
# ✅ GOOD - Preserve existing value
existing_leverage = cache.get(id).leverage
leverage = event.get("l") or existing_leverage # Use existing if update lacks field
```

---

### Pattern 25: Suppressing Empty State Updates (Stuck UI)

**Symptom:** Closing the last item on backend doesn't clear it from UI. UI requires refresh to clear.

**Root Cause:**
```python
# ❌ BAD - conditional broadcast
if items_list:
    broadcast(items_list)
# When list is empty [], block creates False, broadcast skipped.
# Frontend keeps last known list [Item A].
```

**Fix:**
```python
# ✅ GOOD - Always broadcast state
broadcast(items_list) # Sends [] -> Frontend updates to empty
```

---

### Pattern 26: 404 API Error due to Missing Route Prefix in Frontend

**Symptom:** 
- Frontend API call fails with `404 Not Found`.
- Backend logs show the server is running and API is accessible.
- Other endpoints might be working.

**Root Cause:**
```typescript
// Backend routing:
// app.include_router(api_v1_router) -> prefix "/api/v1"
// api_v1_router.include_router(bots_router) -> prefix "/bots"
// Result: /api/v1/bots/...

// Frontend Client:
const API_BASE_URL = 'http://localhost:8000'; // Points to root

// ❌ BAD - Missing intermediate prefix
apiClient.post(`/bots/${id}/positions/close`) 
// Result: http://localhost:8000/bots/... (404)
```

**Fix:**
```typescript
// ✅ GOOD - Include full path
apiClient.post(`/api/v1/bots/${id}/positions/close`)
// Result: http://localhost:8000/api/v1/bots/... (200)
```

**Debugging Approach:**
1. Check `Network` tab in browser for the EXACT URL being requested.
2. Compare with Backend startup logs or `api/docs` (Swagger UI).
3. Verify `apiClient` Base URL configuration.

---

### Pattern 27: Duplicate Router Decorator in Backend

**Symptom:** 
- Confusing route behavior, potential startup warnings, or ignored routes.
- Code looks correct but behaves strangely.

**Root Cause:**
```python
# ❌ BAD - Copy-paste error
@router.get("/{bot_id}/positions")
@router.get("/{bot_id}/positions")  # <-- DUPLICATE
async def get_bot_positions(...):
```

**Fix:**
```python
# ✅ GOOD - Single decorator
@router.get("/{bot_id}/positions")
async def get_bot_positions(...):
```
```

---

### Pattern 28: Missing Required Field in Entity Constructor

**Symptom:** 
`TypeError: __init__() missing 1 required positional argument: 'updated_at'` (or similar field name)

**Root Cause:**
Dataclass entity has non-optional fields that must be provided during instantiation.
```python
@dataclass
class Order:
    updated_at: datetime  # Required field (no default)

# Service Code:
Order(..., created_at=now) # ❌ Missing updated_at so it crashes
```

**Fix:**
```python
Order(..., created_at=now, updated_at=now) # ✅ GOOD
```

**Prevention:**
1. Use factory methods (e.g., `Order.create_market_order`) which usually handle timestamp generation.

---

### Pattern 29: Repository Missing Method (AttributeError)

**Symptom:**
`AttributeError: 'OrderRepository' object has no attribute 'create'`

**Root Cause:**
Service layer uses a Domain-Defined interface (e.g. `repo.create(entity)`), but the Infrastructure implementation only has `add(model)`.
Common when transitioning from direct Model usage to Domain Entities.

**Fix:**
Implement the missing method in Repository, handling Entity -> Model mapping.

```python
# Repository
async def create(self, entity: Entity) -> Entity:
    model = self._map_to_model(entity) # Map fields
    self.session.add(model)
    await self.session.commit()
    return entity
```

---

### Pattern 30: DB Constraint Mismatch with Code Enums

**Symptom:**
`sqlalchemy.exc.IntegrityError: check constraint "ck_orders_side" ... violated`

**Root Cause:**
Database schema constraint (`CHECK side IN ('LONG', 'SHORT')`) did not match the Code Enum definition (`BUY`, `SELL`).
This often happens when constraints are copy-pasted from other tables (e.g. copied from `positions` to `orders`).

**Fix:**
1. Update `models.py` definition.
2. Run migration (ALTER TABLE DROP/ADD CONSTRAINT).
3. Update existing data if necessary.
4. **Crucial**: Ensure Enums in Domain and Model match exactly.

---

### Pattern 31: API Adapter Interface Mismatch & Keyword Arguments

**Symptom:**
`TypeError: create_order() missing 1 required positional argument: 'type'`
OR
API logic error (e.g. wrong position side) because keyword arguments didn't match expected external API keys.

**Root Cause:**
1. **Python Arg Mismatch**: Calling `adapter.func(my_arg=X)` when signature is `def func(arg=X)`.
2. **kwargs Passthrough**: Adapter uses `**kwargs` to pass params directly to API, but Service passes snake_case keys (`position_side`) instead of API's camelCase (`positionSide`).

**Fix:**
1. Check Adapter signature strictly.
2. If Adapter passes `**kwargs` to API, ensure keys match what the API expects EXACTLY.

```python
# ❌ BAD - Snake case ignored by Binance API, and 'type' is missing
adapter.create_order(
    order_type="MARKET", 
    position_side="LONG"
)

# ✅ GOOD - Correct name 'type' and camelCase 'positionSide'
adapter.create_order(
    type="MARKET", 
    positionSide="LONG"
)
```

---

### Pattern 32: Boolean Type in API Params (Signing Error)

**Symptom:**
`Invalid variable type: value should be str, int or float, got True of type <class 'bool'>`

**Root Cause:**
Request signing/hashing functions (like Binance signature generation) usually iterate over params and expect string concatable values. 
Passing a raw Boolean (`True`) causes a type error during signature generation before the request is even sent.

**Fix:**
Explicitly convert booleans to strings (usually lowercase `"true"`/`"false"` for JSON/Query params).

```python
# ❌ BAD
adapter.create_order(..., reduceOnly=True)

# ✅ GOOD
adapter.create_order(..., reduceOnly="true")
```

---

### Pattern 33: Conflicting API Parameters (reduceOnly vs Hedge Mode)

**Symptom:**
`Binance API error 400: {"code":-1106,"msg":"Parameter 'reduceonly' sent when not required."}`

**Root Cause:**
In Binance Futures **Hedge Mode**, you close a position by trading the opposite side ONLY on that specific position (using `positionSide`). 
The `reduceOnly` parameter is **redundant and prohibited** in Hedge Mode. It is only for **One-Way Mode**.

**Fix:**
Remove `reduceOnly` parameter when sending `positionSide`.

```python
# ❌ BAD in Hedge Mode
adapter.create_order(
    positionSide="LONG",
    reduceOnly="true" # Error -1106
)

# ✅ GOOD
adapter.create_order(
    positionSide="LONG"
)
```

---

### Pattern 34: Missing Enum Value in DB Constraint

**Symptom:**
`sqlalchemy.exc.IntegrityError: check constraint "ck_orders_status" ... violated` and log shows `parameters: ('NEW', ...)`.

**Root Cause:**
The Database Check Constraint for a status Enum was missing a valid value used by the application (e.g., `NEW` was missing from the list of allowed statuses).

**Fix:**
1. Update Model definition to include the missing value.
2. Run migration script to DROP and RE-ADD the constraint with the new list of values.
### Pattern 18: Bot Stats Race Condition (Concurrent Updates)

**Symptom:** 
- "Total Trades" count is lower than actual number of trades in history.
- Happens when "Close All" is used or multiple positions close simultaneously.
- Real-time updates show the wrong number.

**Root Cause:**
Concurrency race condition. Multiple requests fetch the bot, read stats, increment values, and save. The last writer wins, overwriting previous increments. 
Database row locking was missing.

```python
# ❌ BAD - No locking, prone to race conditions
result = await self._session.execute(
    select(BotModel).where(BotModel.id == bot_uuid)
)
bot = result.scalar_one_or_none()
bot.total_trades += 1  # If 2 requests do this at once, count only goes up by 1
```

**Fix:**
Use `with_for_update()` to lock the row during the transaction. This forces sequential processing of updates.

```python
# ✅ GOOD - Row locking ensures sequential updates
result = await self._session.execute(
    select(BotModel).where(BotModel.id == bot_uuid).with_for_update()
)
```

**Related Files:**
- `backend/src/trading/application/services/bot_stats_service.py`
### Pattern 18: Bot Stats Race Condition & Missing Commit

**Symptom:** 
- "Total Trades" count is lower than actual number of trades in history.
- Happens when "Close All" is used or multiple positions close simultaneously.
- Real-time updates show the wrong number.
- Even after "race condition" fix with locking, stats persist at old values if page is refreshed.

**Root Cause 1:**
Concurrency race condition. Multiple requests fetch the bot, read stats, increment values, and save. The last writer wins, overwriting previous increments. 
Database row locking was missing.

**Root Cause 2:**
Missing `commit()`. The service used `flush()` instead of `commit()`. `flush()` sends SQL to the database but does not end the transaction. If the caller (UseCase) relies on implicit commit from a context manager that closes *after* the broadcast but *before* the transaction is finalized, or if the session is closed without commit, the changes are rolled back. 
The WebSocket broadcast saw the flashed changes (in-memory) so it sent "20", but the DB remained at "18".

```python
# ❌ BAD - No locking, flush but no commit
async def update_stats(...):
    # ... logic ...
    await self._session.flush() # Only pushes to DB buffer
```

**Fix:**
1. Use `with_for_update()` to lock the row.
2. Use `commit()` to persist changes.

```python
# ✅ GOOD - Row locking + Commit
result = await self._session.execute(
    select(BotModel).where(BotModel.id == bot_uuid).with_for_update()
)
# ... update logic ...
await self._session.commit()
```

**Related Files:**
- `backend/src/trading/application/services/bot_stats_service.py`

### Pattern 20: WebSocket Race Condition (Missing Trade History)

**Symptom:**
- When closing positions (especially "Close All"), some trades are not recorded in the database.
- "Total Trades" count is correct (via WebSocket) but "Trade History" table is missing rows.
- Logs show "Order update for unknown order".

**Root Cause:**
- Race Condition between **Order Creation (REST)** and **Order Update (WebSocket)**.
-  sends order to Binance \u2192 Binance executes \u2192 Binance sends WebSocket event.
- The WebSocket event arrives at  **before** the  has finished committing the new order transaction to the database.
-  queries the DB, finds nothing, and skips trade creation.

**Fix:**
- Implement a **Retry Loop** with backoff in the WebSocket handler.
- If the order is not found, wait (0.5s, 1s, etc.) and retry.

```python
# \u2705 GOOD - Retry loop to handle race condition
retry_count = 0
max_retries = 3
while retry_count < max_retries:
    order = await repo.get(order_id)
    if order:
        break
    await asyncio.sleep(0.5 * (retry_count + 1))
    retry_count += 1
```

**Related Files:**
- `backend/src/trading/infrastructure/websocket/binance_user_stream.py`

---

## Pattern 21: Bot Stats Real-Time Update Not Working (Multi-Layer Bug)

**Symptom:** 
- "Total Trades" in Bot Stats UI doesn't update in real-time after "Close All"
- Trade History shows correct count (e.g., 65) but Bot Stats shows fewer (e.g., 63)
- Stats only update after page refresh

**Root Causes (Multiple layers):**

### Layer 1: `client_order_id` Not Saved to Database
When creating orders, `OrderRepository.create()` was NOT saving `client_order_id` to the database. This meant WebSocket order updates (which lookup by `client_order_id`) could never find matching orders.

```python
# Before (BROKEN):
model = OrderModel(
    id=order.id,
    exchange_order_id=order.exchange_order_id
    # client_order_id was MISSING!
)

# After (FIXED):
model = OrderModel(
    id=order.id,
    client_order_id=order.client_order_id,  # CRITICAL: Required for WebSocket lookup
    exchange_order_id=order.exchange_order_id
)
```

### Layer 2: Trade Creation Not Triggering Stats Update
The `TradeRepository.create()` method was not triggering stats recalculation after saving trades. Added post-commit stats update and WebSocket broadcast:

```python
async def create(self, trade: Trade) -> Trade:
    # ... save trade ...
    await self.session.commit()
    
    # === REAL-TIME STATS UPDATE ===
    if trade.bot_id:
        stats_service = BotStatsService(self.session)
        await stats_service.update_stats_on_trade_close(str(trade.bot_id), trade.realized_pnl)
        
        stats = await stats_service.get_bot_stats(str(trade.bot_id))
        if stats:
            await websocket_manager.broadcast_bot_stats_update(
                user_id=str(trade.user_id),
                bot_id=str(trade.bot_id),
                stats=stats
            )
```

### Layer 3: WebSocket Endpoint Not Registered for Broadcasts (CRITICAL)
The general `/ws` WebSocket endpoint accepted connections but **never registered them with `websocket_manager`**. This meant broadcasts could never reach connected clients!

```python
# Before (BROKEN):
async def websocket_general_endpoint(websocket: WebSocket, token: Optional[str] = None):
    await websocket.accept()
    connection_id = f"{user_id}_{id(websocket)}"  # Local tracking only, not registered!
    # ... handle messages ...
    # NO cleanup on disconnect

# After (FIXED):
async def websocket_general_endpoint(websocket: WebSocket, token: Optional[str] = None):
    await websocket.accept()
    # CRITICAL: Register with websocket_manager so broadcasts can reach this connection
    connection_id = await websocket_manager.connect(websocket, user_id)
    try:
        # ... handle messages ...
    finally:
        # CRITICAL: Unregister on disconnect
        await websocket_manager.disconnect(connection_id)
```

**Debugging Approach:**
1. Add `print()` statements (bypasses logger level filtering) at each layer
2. Trace the flow: API → Order creation → WebSocket event → Order lookup → Trade creation → Stats update → Broadcast
3. Check browser console for WebSocket messages
4. Verify message format matches frontend expectations

**Key Insight:**
This bug required fixing THREE separate issues in sequence:
1. Order lookup failing → Add `client_order_id` to DB
2. Stats not updating → Add post-trade stats recalculation
3. Broadcast not reaching client → Register WebSocket with manager

Each fix alone was not sufficient - all three were required for the complete flow.

**Related Files:**
- `backend/src/trading/infrastructure/persistence/repositories/order_repository.py`
- `backend/src/trading/infrastructure/persistence/repositories/trade_repository.py`
- `backend/src/trading/presentation/controllers/websocket_controller.py`
- `backend/src/trading/infrastructure/websocket/websocket_manager.py`
- `frontend/src/hooks/use-bot-stats-websocket.ts`

---

## Pattern 22: Streak Counter Inflation (Exceeded Total Trades)

**Symptom:**
- Streak shows "108L" but Total Trades is only 69
- Mathematically impossible - streak cannot exceed total trades

**Root Cause:**
The streak was being **incremented** every time `update_stats_on_trade_close()` was called:

```python
# BROKEN: Incremental update
if is_winning:
    bot.current_win_streak = (bot.current_win_streak or 0) + 1  # Called multiple times!
```

But this function was now called multiple times per trade (from both `UpdateOrderStatusUseCase` and `TradeRepository.create()`), causing the streak to inflate.

**Fix:**
Changed from incremental streak updates to **full recalculation from trade history**:

```python
# FIXED: Recalculate from trade history
trades_stmt = select(TradeModel.pnl).where(
    TradeModel.bot_id == bot_uuid
).order_by(TradeModel.executed_at.asc())

all_trades = (await self._session.execute(trades_stmt)).scalars().all()

current_win_streak = 0
current_loss_streak = 0
max_win_streak = 0
max_loss_streak = 0

for pnl in all_trades:
    if pnl and pnl > 0:
        current_win_streak += 1
        current_loss_streak = 0
        max_win_streak = max(max_win_streak, current_win_streak)
    else:
        current_loss_streak += 1
        current_win_streak = 0
        max_loss_streak = max(max_loss_streak, current_loss_streak)

bot.current_win_streak = current_win_streak
bot.current_loss_streak = current_loss_streak
bot.max_win_streak = max_win_streak
bot.max_loss_streak = max_loss_streak
```

**Related Files:**
- `backend/src/trading/application/services/bot_stats_service.py`

---

## Pattern 23: PnL Discrepancy Between Pages

**Symptom:**
- Bot Management page shows P&L: `+$0.00`
- Bot Details page shows P&L: `$-7.62`
- Same bot, different values

**Root Cause:**
- `get_bot` endpoint (Bot Details) recalculates stats before returning
- `get_bots` endpoint (Bot Management) simply returns cached values without recalculation

**Fix:**
Added self-healing stats recalculation to `get_bots` endpoint:

```python
@router.get("/", response_model=List[BotResponse])
async def get_bots(...):
    bots = await get_bots_use_case.execute(...)
    
    # === SELF-HEALING: Recalculate stats for each bot ===
    async with AsyncSessionLocal() as session:
        stats_service = BotStatsService(session)
        for bot in bots:
            await stats_service.update_stats_on_trade_close(str(bot.id), Decimal("0"))
    
    # Re-fetch to get updated stats
    bots = await get_bots_use_case.execute(...)
    return [bot_to_response(bot) for bot in bots]
```

**Key Insight:**
When implementing self-healing statistics, ensure ALL endpoints that display stats use the same recalculation logic. Inconsistent application leads to confusing UI discrepancies.

**Related Files:**
- `backend/src/trading/presentation/controllers/bots.py`

---

## Pattern 24: PnL Discrepancy Between Pages (Field Name Mismatch)

**Symptom:**
- Bot Management page shows P&L: `+$0.00`
- Bot Details page shows P&L: `$-7.62`
- API Network tab shows correct value in response

**Root Cause:**
Frontend was looking for the wrong field name:
- API returns: `total_profit_loss: -7.67`
- Frontend expected: `bot.total_pnl` (wrong field name!)

```typescript
// BROKEN: Wrong field name
const totalPnl = parseFloat(String(bot.total_pnl ?? 0)) || 0;

// FIXED: Use correct field name from API
const totalPnl = parseFloat(String(bot.total_profit_loss ?? 0)) || 0;
```

**Debugging Approach (Recommended Order):**

1. **Check Network Tab First** (saves 80% of debugging time!)
   - Open Chrome DevTools → Network tab
   - Look at the API response JSON
   - Verify the actual field names and values returned

2. **Compare Field Names**
   - API response field: `total_profit_loss`
   - Frontend access pattern: `bot.total_pnl`
   - If they differ → Field name mismatch!

3. **Trace from API to UI**
   - Backend: What field name is being serialized?
   - Frontend: What field name is being read?
   - Types: Is there a TypeScript interface that should match the API?

**Key Lesson:**
When data is "missing" on the frontend but present in API response:
1. DON'T immediately add debug prints to backend
2. DO check Network tab first to see what's actually being returned
3. DO compare field names between API response and frontend code

**Related Files:**
- `frontend/src/pages/Bots.tsx` (frontend field access)
- `backend/src/trading/presentation/controllers/bots.py` (API response schema)

---

## Debugging Tips Summary

When debugging data discrepancies in the UI:

1. **API Network Tab First** - Always check what the API returns before adding backend debug code

2. **Field Name Verification** - Compare API field names with frontend access patterns

3. **Browser Console** - For WebSocket issues, add temporary console.log to see message structure

4. **Database Query** - Use a quick Python script to check raw DB values

5. **Only Add Backend Debug Prints as Last Resort** - They're expensive to add/remove and slow down debugging

**Time-Saving Priority:**
1. Network Tab (10 seconds)
2. Browser Console (30 seconds)
3. Database Query (1 minute)
4. Backend Debug Prints (5+ minutes each iteration)
