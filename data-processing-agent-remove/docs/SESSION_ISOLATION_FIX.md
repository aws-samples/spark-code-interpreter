# Session Isolation Fix

## Problem

Session isolation was broken - code was generated using CSV from previous prompt instead of tables selected for current prompt.

**Root Cause**: CSV and tables were not mutually exclusive. When tables were selected, the old CSV remained in the session, and vice versa.

## Solution

Made CSV and tables **mutually exclusive** - selecting one automatically clears the other.

## Changes Made

### Backend (main.py)

**1. Clear CSV when tables are selected:**
```python
@app.post("/sessions/{session_id}/select-tables")
async def select_tables(...):
    session.selected_tables = selected_tables
    
    # Clear CSV when tables are selected (session isolation)
    if selected_tables:
        session.uploaded_csv = None
        print(f"🧹 Cleared CSV (selected {len(selected_tables)} tables)")
```

**2. Clear tables when CSV is uploaded:**
```python
@app.post("/upload-csv")
async def upload_csv(...):
    session.uploaded_csv = {...}
    
    # Clear tables when CSV is uploaded (session isolation)
    session.selected_tables = []
    print(f"✅ Uploaded CSV to {s3_path} (cleared tables)")
```

### Frontend (App.jsx)

**1. Clear CSV when tables are selected:**
```javascript
onTablesSelected={(tables) => {
  setSelectedTables(tables);
  // Clear CSV when tables are selected (session isolation)
  if (tables.length > 0) {
    setUploadedCsv(null);
  }
  ...
}}
```

**2. Clear tables when CSV is uploaded:**
```javascript
const handleCsvUpload = async (file) => {
  ...
  setUploadedCsv({...});
  // Clear tables when CSV is uploaded (session isolation)
  setSelectedTables([]);
  setResetKey(prev => prev + 1);
  ...
}
```

## Session Lifecycle (Fixed)

### Scenario 1: CSV → Tables
```
1. Upload CSV
   → session.uploaded_csv = {data}
   → session.selected_tables = []  ✅ CLEARED

2. Select tables
   → session.selected_tables = [tables]
   → session.uploaded_csv = None  ✅ CLEARED

3. Generate code
   → Uses ONLY tables (CSV is None)
```

### Scenario 2: Tables → CSV
```
1. Select tables
   → session.selected_tables = [tables]
   → session.uploaded_csv = None

2. Upload CSV
   → session.uploaded_csv = {data}
   → session.selected_tables = []  ✅ CLEARED

3. Generate code
   → Uses ONLY CSV (tables is [])
```

### Scenario 3: After Execution
```
1. Execute code
   → Clears both CSV and tables
   → session.uploaded_csv = None
   → session.selected_tables = []

2. Next prompt
   → Must upload CSV OR select tables again
   → Clean slate for each generation
```

## Mutual Exclusivity

| Action | CSV State | Tables State |
|--------|-----------|--------------|
| Upload CSV | ✅ Set | ❌ Cleared |
| Select Tables | ❌ Cleared | ✅ Set |
| Execute Code | ❌ Cleared | ❌ Cleared |

## Testing

```bash
# Run test
python3 test_session_isolation_fix.py

# Expected output:
✅ ALL TESTS PASSED

Session isolation is working correctly:
  • CSV and tables are mutually exclusive
  • Selecting one clears the other
  • Each prompt uses only the current data source
```

## Manual Testing

### Test 1: CSV → Tables
1. Upload CSV file
2. Generate code → should use CSV
3. Select Glue tables
4. Generate code → should use tables (NOT CSV)

### Test 2: Tables → CSV
1. Select Glue tables
2. Generate code → should use tables
3. Upload CSV file
4. Generate code → should use CSV (NOT tables)

### Test 3: After Execution
1. Upload CSV and generate code
2. After execution, select tables
3. Generate code → should use tables (NOT old CSV)

## Verification

Check backend logs for:
```
✅ Uploaded CSV to s3://... (cleared tables)
🧹 Cleared CSV (selected 2 tables)
📊 Session state before generation:
   - CSV: None (or filename)
   - Tables: 0 selected (or N selected)
```

## Summary

✅ **Fixed**: CSV and tables are now mutually exclusive
✅ **Backend**: Clears opposite data source on selection
✅ **Frontend**: Syncs UI state with backend
✅ **Session isolation**: Each prompt uses only current data source

The fix ensures that each code generation uses ONLY the data source selected for that specific prompt, not leftover data from previous prompts.
