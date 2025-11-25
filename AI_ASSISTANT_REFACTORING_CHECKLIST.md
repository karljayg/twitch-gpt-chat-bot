# AI Assistant Refactoring Checklist
## Mandatory Steps - NO EXCEPTIONS

When migrating, refactoring, or rewriting ANY code that already exists, **ALWAYS** follow this process:

---

## PHASE 1: AUDIT (Before Writing ANY New Code)

### Step 1: Read ALL Legacy Code
- [ ] Read the ENTIRE legacy file/function being migrated
- [ ] Don't just skim - read every line
- [ ] Pay attention to comments (they often explain WHY things exist)

### Step 2: Identify ALL Defensive Patterns
Look for and document:
- [ ] **Validation checks** (if not X, return/error)
- [ ] **Sanitization** (clean_text, replace_non_ascii, strip, etc.)
- [ ] **Confirmation prompts** (Y/N before destructive actions)
- [ ] **Retry logic** (try multiple times, fallbacks)
- [ ] **Error handling** (try/except blocks - note what they catch and why)
- [ ] **Edge case handling** (empty results, None checks, type conversions)
- [ ] **State checks** (existing_comment, first_run, pending flags)
- [ ] **Timeouts** (context_age checks, session expiry)

### Step 3: Identify ALL Side Effects
- [ ] Database updates
- [ ] File writes
- [ ] External API calls
- [ ] State mutations (setting flags, clearing contexts)
- [ ] Logging statements (especially with sanitization)

### Step 4: Document Findings
Create a quick list:
```
Legacy function: process_player_comment()
Business logic: Save comment to DB
Defensive patterns:
  1. Check if comment already exists (line 388)
  2. Ask Y/N confirmation before overwrite (line 396)
  3. Store pending state for confirmation (line 390-394)
  4. Sanitize before logging (line 919)
  5. Validate comment not empty (line 346)
Edge cases:
  - No replay found
  - Comment text is empty
  - User says 'yes' without context
```

---

## PHASE 2: DESIGN (Plan New Code)

### Step 5: Map ALL Patterns to New Architecture
For EACH defensive pattern identified:
- [ ] Decide where it goes in new code
- [ ] Ensure it's not accidentally skipped
- [ ] Note any dependencies (e.g., needs access to twitch_bot instance)

---

## PHASE 3: IMPLEMENT (Write New Code)

### Step 6: Write Code with ALL Patterns
- [ ] Implement business logic
- [ ] Implement EVERY defensive pattern from Step 2
- [ ] Implement EVERY side effect from Step 3
- [ ] Add comments explaining WHY patterns exist

### Step 7: Self-Review Before Submitting
**Mandatory self-check:**
- [ ] Compare new code line-by-line with legacy
- [ ] Verify every if/elif/else branch is accounted for
- [ ] Verify every try/except is migrated
- [ ] Verify every validation check exists
- [ ] Check for "simplified" code that might have dropped patterns

---

## PHASE 4: VERIFY (After Code Written)

### Step 8: Test Edge Cases
- [ ] Test with empty input
- [ ] Test with existing data (should ask confirmation)
- [ ] Test with Unicode characters
- [ ] Test error paths
- [ ] Test None/null cases

---

## Common Mistakes to AVOID

### ❌ "Simplifying" by removing checks
```python
# Legacy (defensive)
if existing_comment:
    ask_confirmation()
    return
save_comment()

# BAD refactor (too "clean")
save_comment()  # Oops, lost the check!
```

### ❌ Assuming "it's obvious"
```python
# Legacy
# replace with ? all non ascii characters that throw an error in logger
response = replace_non_ascii(response)

# BAD refactor - "I don't need that comment"
# (Forgets to add the sanitization entirely)
```

### ❌ "The architecture handles it"
```python
# Legacy checks for None explicitly
if result is None:
    return error

# BAD refactor - "My new function returns Optional, it's handled"
# (But caller doesn't check for None, crashes later)
```

---

## Red Flags That Should Trigger Extra Scrutiny

If you see ANY of these in legacy code, STOP and pay extra attention:

1. **Comments with "fix", "workaround", "bug", "handle", "prevent"**
   - Someone learned a painful lesson here
   - Don't repeat their pain

2. **Multiple try/except blocks**
   - Each one is handling a real failure mode
   - Don't assume "it won't fail"

3. **Confirmation prompts (Y/N)**
   - There's a reason it asks
   - Don't make it silent

4. **Sanitization before logging**
   - Unicode errors are real
   - Windows console is painful

5. **State flags (pending_X, first_run, context)**
   - Complex state machines exist for a reason
   - Don't simplify away the state

6. **if existing_X checks**
   - Overwriting data is destructive
   - Always check first

7. **Time/age checks (context_age, timestamp)**
   - Stale state causes bugs
   - Keep the timeout logic

---

## Specific Patterns to NEVER Forget

### Pattern: Overwrite Protection
```python
# ALWAYS check before destructive updates
existing_data = get_existing()
if existing_data:
    confirm = ask_user_confirmation()
    if not confirm:
        return
# Now safe to overwrite
```

### Pattern: Unicode Logging Safety
```python
# ALWAYS sanitize before logging user content
safe_message = replace_non_ascii(message, replacement='?')
logger.info(f"Sent: {safe_message}")
```

### Pattern: Empty Input Validation
```python
# ALWAYS validate before processing
if not input_text or not input_text.strip():
    return error("Please provide input")
```

### Pattern: State Expiry
```python
# ALWAYS check state freshness
if context and (time.now() - context['timestamp']) < TIMEOUT:
    use_context()
else:
    clear_stale_context()
```

---

## When In Doubt

**Ask yourself:**
1. "What could go wrong?"
2. "What did the original developer worry about?"
3. "Why is this try/except here?"
4. "Why does it ask for confirmation?"
5. "What happens if this is None?"

**If you can't answer these, read more legacy code.**

---

## Accountability

**Every time a bug reappears:**
1. Document it in MIGRATION_LESSONS_LEARNED.md
2. Add the pattern to this checklist
3. Review what step in the process was skipped

**Goal: Zero regressions**

---

## Commitment

As an AI assistant working on this codebase, I commit to:

1. ✅ **ALWAYS** follow this checklist when refactoring
2. ✅ **NEVER** skip the audit phase
3. ✅ **ALWAYS** compare new code to legacy line-by-line
4. ✅ **ALWAYS** preserve defensive patterns
5. ✅ **NEVER** assume "it's obvious" or "architecture handles it"

**If I submit code that loses a defensive pattern, I have failed.**

---

**Last Updated**: November 24, 2025  
**Status**: MANDATORY - Follow this EVERY TIME




