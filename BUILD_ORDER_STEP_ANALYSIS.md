
# Build Order Step Count Analysis & Recommendations

## Current State

### Step Count Usage Across Codebase

1. **Storage (Replay Summaries)**
   - `api/sc2_game_utils.py` (lines 301-312): Dynamic based on game length
     - Short games (<600s): **120 steps**
     - Long games (>=600s): **180 steps**
     - Team games (>2 players): Half of above
   - `core/game_summarizer.py` (lines 50-59): Same logic

2. **Pattern Learning (Creating Signatures)**
   - `api/pattern_learning.py` (line 446): Uses `config.BUILD_ORDER_COUNT_TO_ANALYZE` = **60 steps**
   - Creates signatures with only first 60 steps
   - **Issue**: Inconsistent with storage (120/180) and matching (up to 120)

3. **Pattern Matching (Comparison)**
   - `api/ml_opponent_analyzer.py` (lines 406-413): "FAIR COMPARISON"
     - Limits comparison to pattern's actual step count
     - Caps at **120 steps** maximum
     - If pattern has 60 steps, compares only first 60 of new build
     - If pattern has 120 steps, compares first 120
   
4. **Strategic Item Extraction**
   - `api/ml_opponent_analyzer.py` (line 547): Hard-coded **120 steps** limit
   - `_extract_strategic_items_from_build()`: Always limits to first 120 steps

5. **Database Extraction**
   - `models/mathison_db.py` (line 762): Uses `config.BUILD_ORDER_COUNT_TO_ANALYZE` = **60 steps**
   - Extracts only 60 steps from DB replay summaries

### Similarity Calculation

- Uses bidirectional weighted matching
- Weighted by timing (earlier = more important) and tech buildings
- No adjustment for step count differences between old/new patterns
- **Issue**: Comparing 30-step old pattern vs 120-step new build can give inflated similarity if early game matches well

---

## Problems Identified

1. **Inconsistency**: Pattern signatures stored with 60 steps, but matching can use up to 120
2. **Legacy Data**: Old patterns may have 30-60 steps, new ones will have 120
3. **Similarity Inflation**: Short patterns (30-40 steps) matching well on early game can get high similarity scores even though mid-game may differ significantly
4. **Missing Context**: No distinction between "early game match" (first 30 steps) vs "full match" (120 steps)

---

## Recommendations

### 1. Standardize to 120 Steps Everywhere

**Changes needed:**

- **Update `config.BUILD_ORDER_COUNT_TO_ANALYZE` from 60 → 120**
  - This affects:
    - `api/pattern_learning.py` (pattern signature creation)
    - `models/mathison_db.py` (DB extraction)
    - Any other code using this config

- **Keep dynamic storage (120/180)** in replay summaries
  - But for pattern matching, always use 120 steps
  - Rationale: 120 steps captures early-mid game (~6-8 minutes), which is where strategic decisions are made
  - For longer games, we still store 180 in summary but use first 120 for matching

### 2. Adjust Similarity % Based on Pattern Step Count

**Similarity Adjustment Formula:**

When comparing patterns, apply a confidence multiplier based on how much data we have:

```python
def calculate_step_count_adjustment(pattern_step_count, min_steps_for_full_confidence=80):
    """
    Adjust similarity score based on pattern step count.
    
    Patterns with fewer steps get lower confidence multipliers:
    - 80+ steps: 100% confidence (no adjustment)
    - 60-79 steps: 90% confidence
    - 40-59 steps: 75% confidence  
    - 20-39 steps: 60% confidence (early game match only)
    - <20 steps: 40% confidence (very limited data)
    
    Rationale:
    - Short patterns (30 steps) only capture opening (~2-3 min)
    - Medium patterns (60 steps) capture early game (~4-5 min)
    - Full patterns (120 steps) capture early-mid game (~6-8 min)
    - We want to distinguish "good early match" from "good overall match"
    """
    if pattern_step_count >= min_steps_for_full_confidence:
        return 1.0  # Full confidence
    elif pattern_step_count >= 60:
        return 0.90  # High confidence (early game well covered)
    elif pattern_step_count >= 40:
        return 0.75  # Medium confidence (opening covered, mid-game unclear)
    elif pattern_step_count >= 20:
        return 0.60  # Low confidence (early opening only)
    else:
        return 0.40  # Very low confidence (very limited data)
```

**Apply in `_compare_build_signatures()`:**
- Calculate raw similarity as currently done
- Multiply by adjustment factor based on `len(pattern_early_game)`
- This gives realistic similarity scores that reflect data quality

### 3. Match Classification System

Add classification to match results to indicate match quality:

```python
def classify_match_quality(similarity_score, pattern_step_count):
    """
    Classify match quality based on similarity and data available.
    """
    if pattern_step_count >= 80:
        if similarity_score >= 0.75:
            return "Strong Full Match"
        elif similarity_score >= 0.60:
            return "Good Full Match"
        elif similarity_score >= 0.45:
            return "Moderate Full Match"
        else:
            return "Weak Full Match"
    elif pattern_step_count >= 40:
        if similarity_score >= 0.70:
            return "Strong Early-Mid Match"
        elif similarity_score >= 0.55:
            return "Good Early-Mid Match"
        else:
            return "Weak Early-Mid Match"
    else:  # < 40 steps
        if similarity_score >= 0.65:
            return "Strong Early Match"
        elif similarity_score >= 0.50:
            return "Good Early Match"
        else:
            return "Weak Early Match"
```

### 4. Implementation Plan

**Phase 1: Standardize to 120 Steps**
1. Update `BUILD_ORDER_COUNT_TO_ANALYZE = 120` in config
2. Update `api/pattern_learning.py` line 446 to use 120 (already uses config, so just config change needed)
3. Verify `api/ml_opponent_analyzer.py` line 409 cap at 120 is correct (it is)
4. Update `models/mathison_db.py` line 762 (uses config, so just config change needed)
5. Update `_extract_strategic_items_from_build()` line 547: Already uses 120, no change needed

**Phase 2: Add Similarity Adjustment**
1. Add `calculate_step_count_adjustment()` function to `ml_opponent_analyzer.py`
2. Modify `_match_build_against_patterns()` to:
   - Get pattern step count: `len(pattern_early_game)`
   - Calculate adjustment factor
   - Apply adjustment after similarity calculation
   - Store original and adjusted similarity in match results
3. Add `classify_match_quality()` function for match classification
4. Update match result structure to include:
   - `similarity_raw`: Original similarity (0-1)
   - `similarity_adjusted`: After step count adjustment (0-1)
   - `match_quality`: Classification string
   - `pattern_step_count`: For reference

**Phase 3: Backward Compatibility**
- Old patterns with <120 steps will still work
- They'll get appropriate confidence adjustments
- New patterns will use full 120 steps

---

## Code Locations to Modify

1. **`settings/config.py`**: Change `BUILD_ORDER_COUNT_TO_ANALYZE = 120`
2. **`api/ml_opponent_analyzer.py`**:
   - Add `calculate_step_count_adjustment()` function
   - Modify `_match_build_against_patterns()` to apply adjustment
   - Update match result structure
3. **`api/pattern_learning.py`**: Already uses config, no code change needed (just config change)
4. **`models/mathison_db.py`**: Already uses config, no code change needed (just config change)

---

## Expected Outcomes

1. **Consistency**: All new patterns stored with 120 steps
2. **Fair Matching**: Old patterns (30-60 steps) get appropriate confidence adjustments
3. **Clear Results**: Match quality classification helps understand match reliability
4. **Backward Compatible**: Old patterns still work, just with adjusted confidence
5. **Better Accuracy**: Similarity scores more accurately reflect how much of the game was actually compared

