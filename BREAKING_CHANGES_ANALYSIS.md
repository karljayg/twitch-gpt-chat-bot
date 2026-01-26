# Breaking Changes Analysis: BUILD_ORDER_COUNT_TO_ANALYZE 60→120

## ⚠️ CRITICAL FINDING: Config Used for TWO Different Purposes

### 1. Step Count (Array Slicing) - Safe to Change
These locations use `BUILD_ORDER_COUNT_TO_ANALYZE` for array slicing:
- ✅ `api/pattern_learning.py` line 446: `build_data[:config.BUILD_ORDER_COUNT_TO_ANALYZE]` - **SAFE**
- ✅ `models/mathison_db.py` line 762: `reformatted_list[1:config.BUILD_ORDER_COUNT_TO_ANALYZE]` - **SAFE**
- ✅ `utils/load_replays.py` line 168: Used as step count limit - **SAFE**

### 2. Supply Threshold (Filtering) - ⚠️ **WILL BREAK**
These locations use `BUILD_ORDER_COUNT_TO_ANALYZE` as a **supply threshold** (not step count):

- ❌ `api/pattern_learning.py` line 275:
  ```python
  early_build = [step['name'] for step in build_data 
                 if step.get('supply', 0) <= config.BUILD_ORDER_COUNT_TO_ANALYZE]
  ```
  **Problem**: Currently filters to supply ≤60. Changing to 120 would analyze much later game.
  
- ❌ `api/pattern_learning.py` line 306:
  ```python
  early_build = [step['name'] for step in build_data 
                 if step.get('supply', 0) <= config.BUILD_ORDER_COUNT_TO_ANALYZE]
  ```
  **Problem**: Same issue - used for AI confidence calculation

**Impact**: These functions are meant to analyze "early game" (first 60 supply ≈ 2-3 minutes). Changing to 120 supply would analyze mid-game (≈4-5 minutes), completely changing the behavior.

---

## What Would Break

### Direct Breakage
1. **Pattern Learning - Strategy Classification**
   - `_guess_strategy_from_build()` would analyze up to 120 supply instead of 60
   - Would classify builds as "early aggression" even if aggression happens at supply 80-100
   - Changes the meaning of "early game" classification

2. **Pattern Learning - AI Confidence**
   - `_calculate_ai_confidence()` would use 120 supply threshold
   - Confidence scores would be calculated differently
   - Might give false confidence for longer builds

### Indirect Breakage
3. **Existing Pattern Data**
   - Old patterns created with 60-step signatures would still work (backward compatible)
   - But new patterns would have 120 steps, creating inconsistency
   - **This is expected and OK** - the similarity adjustment handles this

4. **Tests**
   - No tests currently check supply threshold behavior
   - Tests in `test_ml_opponent_analyzer.py` use small build orders (don't test step counts)
   - Would need new tests to verify behavior

---

## Recommended Solution

### Option 1: Split Configuration (RECOMMENDED)
Create two separate config values:

```python
# For step count (array slicing)
BUILD_ORDER_STEPS_TO_ANALYZE = 120  # New config

# For supply threshold (early game filtering)
EARLY_GAME_SUPPLY_THRESHOLD = 60  # New config (keep current behavior)
```

Then:
- Update step-count usages to `BUILD_ORDER_STEPS_TO_ANALYZE`
- Keep supply-threshold usages as `EARLY_GAME_SUPPLY_THRESHOLD` (stay at 60)

**Pros**: 
- Clear separation of concerns
- No breaking changes
- Allows independent tuning

**Cons**:
- More config values to manage
- Need to update multiple files

### Option 2: Fix Pattern Learning to Use Step Count
Change lines 275 and 306 to use step count instead of supply:

```python
# OLD (supply-based):
early_build = [step['name'] for step in build_data 
               if step.get('supply', 0) <= config.BUILD_ORDER_COUNT_TO_ANALYZE]

# NEW (step-based):
early_build = [step['name'] for step in build_data[:config.BUILD_ORDER_COUNT_TO_ANALYZE]]
```

**Pros**:
- Uses config consistently for step count
- Simpler (one config value)

**Cons**:
- Changes behavior of these functions (from supply 60 → 120 steps)
- 120 steps might be too much for "early game" classification
- Might break existing pattern learning logic

### Option 3: Keep Config at 60, Use Hard-coded 120 Where Needed
Keep `BUILD_ORDER_COUNT_TO_ANALYZE = 60` for supply threshold.
Use hard-coded 120 for step counts where we want more data.

**Pros**:
- Minimal changes
- No breaking changes

**Cons**:
- Inconsistent (magic numbers)
- Doesn't solve the original problem

---

## Recommended Approach: Option 1 (Split Config)

### Files to Update

1. **`settings/config.py`**:
   ```python
   BUILD_ORDER_STEPS_TO_ANALYZE = 120  # Step count for array slicing
   EARLY_GAME_SUPPLY_THRESHOLD = 60     # Supply threshold for early game analysis
   ```

2. **`api/pattern_learning.py`**:
   - Line 275: Change to `EARLY_GAME_SUPPLY_THRESHOLD`
   - Line 306: Change to `EARLY_GAME_SUPPLY_THRESHOLD`
   - Line 446: Change to `BUILD_ORDER_STEPS_TO_ANALYZE`

3. **`models/mathison_db.py`**:
   - Line 762: Change to `BUILD_ORDER_STEPS_TO_ANALYZE`

4. **`utils/load_replays.py`**:
   - Line 168: Change to `BUILD_ORDER_STEPS_TO_ANALYZE`

5. **`api/game_event_utils/game_started_handler.py`**:
   - Line 194 comment: Update documentation

---

## Tests Needed

### Existing Tests (Should Still Pass)
- `test_ml_opponent_analyzer.py`: Tests don't depend on step count
- Pattern matching tests: Use small build orders, should work with 120 steps

### New Tests Needed

1. **Supply Threshold Test**:
   ```python
   def test_early_game_supply_threshold():
       """Verify early game analysis uses correct supply threshold"""
       build_data = [{"supply": i, "name": f"Unit{i}"} for i in range(1, 150)]
       early_build = [step['name'] for step in build_data 
                      if step.get('supply', 0) <= config.EARLY_GAME_SUPPLY_THRESHOLD]
       assert len(early_build) <= 60, "Should filter to supply 60"
   ```

2. **Step Count Test**:
   ```python
   def test_pattern_signature_uses_step_count():
       """Verify pattern signatures use correct step count"""
       build_data = [{"name": f"Unit{i}"} for i in range(200)]
       signature = learner._create_pattern_signature(build_data)
       assert len(signature['early_game']) <= 120, "Should use 120 steps"
   ```

3. **Similarity Adjustment Test**:
   ```python
   def test_similarity_adjustment_short_pattern():
       """Verify short patterns get similarity adjustment"""
       short_pattern = {"early_game": [{"unit": "RoachWarren"}] * 30}
       long_pattern = {"early_game": [{"unit": "RoachWarren"}] * 120}
       # Test that short pattern gets lower adjusted similarity
   ```

---

## Migration Strategy

1. **Phase 1**: Add new configs, keep old one for backward compat
2. **Phase 2**: Update code to use new configs
3. **Phase 3**: Add tests
4. **Phase 4**: Run against real data to verify behavior
5. **Phase 5**: Remove old config (optional)

---

## Risk Assessment

| Change | Risk Level | Impact | Mitigation |
|--------|-----------|--------|------------|
| Split config | Low | Minimal | Backward compatible, clear naming |
| Update step counts to 120 | Medium | Pattern signatures change | Expected, similarity adjustment handles it |
| Keep supply threshold at 60 | Low | None | Maintains current behavior |
| Add similarity adjustment | Medium | Scoring changes | Can tune multipliers based on results |

