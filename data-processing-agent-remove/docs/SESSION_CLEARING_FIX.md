# Session Clearing Fix

## Problem
CSV from previous prompt was still being used even after execution completed and tables were selected for the next prompt.

## Root Cause
Session clearing was only happening if `execution_result['success']` was True. If execution failed or had any issues, the session was NOT cleared, causing data sources to persist across prompts.

## Fix Applied

### Before (Broken)
```python
if execution_result['success']:
    # Store results
    # Clear session HERE (only on success)
    session.uploaded_csv = None
    session.selected_tables = []
else:
    # Return error
    # NO CLEARING - session persists!
```

### After (Fixed)
```python
# Execute code
execution_result = await execute_code_on_cluster(code, session_id)

# Capture before clearing
csv_used = session.uploaded_csv['filename'] if session.uploaded_csv else None
tables_used = len(session.selected_tables)

# ALWAYS clear (success OR failure)
session.uploaded_csv = None
session.selected_tables = []
print(f"🧹 Cleared session data sources (CSV: {csv_used}, Tables: {tables_used})")

if execution_result['success']:
    # Store successful results
else:
    # Store failed results
```

## Key Changes

1. **Moved clearing BEFORE success check** - happens regardless of outcome
2. **Capture data source info first** - before clearing for logging
3. **Store failed executions** - track failures in history too
4. **Enhanced logging** - shows both CSV and table count

## Expected Behavior

### Scenario 1: Success
```
1. Upload CSV → execute → SUCCESS
   → 🧹 Cleared session (CSV: test.csv, Tables: 0)
2. Select tables → execute
   → Uses tables (CSV is None)
```

### Scenario 2: Failure
```
1. Upload CSV → execute → FAILURE
   → 🧹 Cleared session (CSV: test.csv, Tables: 0)
2. Select tables → execute
   → Uses tables (CSV is None)
```

### Scenario 3: Both Data Sources
```
1. Upload CSV + Select tables → execute → SUCCESS
   → 🧹 Cleared session (CSV: test.csv, Tables: 2)
2. Next prompt
   → Clean slate (CSV: None, Tables: 0)
```

## Testing

### Automated Test
```bash
python3 test_clearing.py
```

Expected output:
```
✅ SUCCESS: Code uses tables, not CSV
Session isolation is working correctly!
```

### Manual Test
1. Upload CSV file
2. Generate code (any prompt)
3. Wait for execution to complete
4. Check backend logs for: `🧹 Cleared session data sources`
5. Select Glue tables
6. Check backend logs for: `Current CSV: None`
7. Generate code
8. Check backend logs for: `CSV: None` and `Tables: 1 selected`
9. Verify generated code references table, NOT CSV

## Backend Logs to Check

### After Execution (Step 2)
```
🚀 Executing final validated code...
✅ Code generation and execution successful
🧹 Cleared session data sources (CSV: test.csv, Tables: 0)
```

### After Table Selection (Step 3)
```
✅ Selected 1 tables:
   • northwind.dow_jones → s3://location
   Current CSV: None  ← MUST BE NONE
```

### Before Next Generation (Step 4)
```
📊 Session state before generation:
   - CSV: None  ← MUST BE NONE
   - CSV S3: None
   - Tables: 1 selected
     • northwind.dow_jones
```

## Verification Checklist

- [ ] Backend logs show `🧹 Cleared` after EVERY execution
- [ ] Table selection shows `Current CSV: None`
- [ ] Next generation shows `CSV: None` in session state
- [ ] Generated code references tables, NOT CSV
- [ ] Test script passes with `✅ SUCCESS`

## Summary

✅ **Fixed**: Session now clears ALWAYS after execution (success or failure)
✅ **Moved**: Clearing happens before success check
✅ **Enhanced**: Better logging shows what was cleared
✅ **Tracked**: Failed executions also stored in history

The fix ensures proper session isolation by clearing data sources after EVERY execution, not just successful ones.
