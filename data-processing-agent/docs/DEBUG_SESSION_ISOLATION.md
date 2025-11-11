# Debug Session Isolation

## Issue
CSV from previous prompt is being used instead of tables selected for current prompt.

## Enhanced Logging Added

### 1. Session State Before Generation
```
📊 Session state before generation:
   - CSV: filename.csv (or None)
   - CSV S3: s3://bucket/path (or None)
   - Tables: 2 selected (or 0)
     • database.table1
     • database.table2
```

### 2. Table Selection
```
✅ Selected 2 tables:
   • database.table1 → s3://location1
   • database.table2 → s3://location2
   Current CSV: filename.csv (or None)
```

### 3. CSV Upload
```
✅ Uploaded CSV to s3://bucket/path
   Current tables: 2 selected (or 0)
```

### 4. After Execution
```
🧹 Cleared session data sources (CSV was: filename.csv or None)
```

## Test Script

Run the debug script to trace session state:

```bash
python3 debug_session.py
```

This will:
1. Upload CSV
2. Generate code (should use CSV)
3. Clear session after execution
4. Select tables
5. Generate code (should use tables, NOT CSV)

## Expected Backend Logs

### First Generation (CSV)
```
📊 Session state before generation:
   - CSV: test.csv
   - CSV S3: s3://bucket/uploads/session/test.csv
   - Tables: 0 selected

🧹 Cleared session data sources (CSV was: test.csv)
```

### Table Selection
```
✅ Selected 1 tables:
   • northwind.dow_jones → s3://location
   Current CSV: None  ← SHOULD BE NONE
```

### Second Generation (Tables)
```
📊 Session state before generation:
   - CSV: None  ← SHOULD BE NONE
   - CSV S3: None
   - Tables: 1 selected
     • northwind.dow_jones
```

## What to Check

### 1. Is Clearing Happening?
Look for: `🧹 Cleared session data sources`

If NOT present → clearing code not being executed

### 2. Is CSV Still Present After Clearing?
After first execution, table selection should show:
```
Current CSV: None
```

If shows filename → clearing not working

### 3. Is Agent Using Correct Data?
Second generation should show:
```
📊 Session state before generation:
   - CSV: None
   - Tables: 1 selected
```

If CSV is not None → session not cleared properly

## Possible Issues

### Issue 1: Clearing Not Called
**Symptom**: No `🧹 Cleared` message in logs
**Cause**: Execution not reaching clearing code
**Fix**: Check if execution_result['success'] is True

### Issue 2: Session Not Persisting
**Symptom**: Tables show 0 after selection
**Cause**: Session object not being saved
**Fix**: Verify sessions dict is being updated

### Issue 3: Frontend Not Syncing
**Symptom**: Backend clears but frontend still shows data
**Cause**: Frontend state not updated
**Fix**: Check setUploadedCsv(null) and setSelectedTables([])

### Issue 4: Agent Caching
**Symptom**: Agent uses old data despite session being cleared
**Cause**: Agent tool caching session data
**Fix**: Agent should call get_data_sources fresh each time

## Manual Test

1. **Start backend with logging**:
   ```bash
   cd backend
   python3 -m uvicorn main:app --reload --port 8000
   ```

2. **In UI**:
   - Upload CSV
   - Generate code
   - Wait for execution to complete
   - Check backend logs for `🧹 Cleared`
   - Select tables
   - Check backend logs for `Current CSV: None`
   - Generate code
   - Check backend logs show `CSV: None` and `Tables: 1 selected`

3. **Expected Result**:
   - Second generation uses tables, NOT CSV
   - Code should reference table, not CSV file

## Quick Fix Test

If issue persists, add explicit clearing before generation:

```python
# In generate endpoint, before agent invocation
if request.clear_previous:
    session.uploaded_csv = None
    session.selected_tables = []
```

Then test with:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "session_id": "test", "clear_previous": true}'
```
