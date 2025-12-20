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

---

**Last Updated:** 2025-12-20  
**Contributors:** Development Team
