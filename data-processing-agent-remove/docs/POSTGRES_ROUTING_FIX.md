# PostgreSQL Routing Fix

## Problem
PostgreSQL workloads were being routed to Lambda code interpreter instead of EMR Serverless, causing failures because:
- Lambda doesn't have VPC access to PostgreSQL databases
- Lambda doesn't have Secrets Manager permissions for PostgreSQL credentials

## Root Cause
Frontend was not sending `selected_postgres_tables` parameter to the backend API.

## Solution

### 1. Frontend Fix (frontend/src/services/api.js)
Added `selected_postgres_tables` parameter to `generateSparkCode` function:

```javascript
export const generateSparkCode = async (prompt, sessionId, s3InputPath = null, selectedTables = null, selectedPostgresTables = null, executionEngine = 'auto') => {
  const response = await fetch(`${API_BASE_URL}/spark/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      prompt, 
      session_id: sessionId,
      s3_input_path: s3InputPath,
      selected_tables: selectedTables,
      selected_postgres_tables: selectedPostgresTables,  // ← ADDED
      execution_engine: executionEngine
    })
  });
```

### 2. Frontend Call Site Fix (frontend/src/App.jsx)
Pass `selectedPostgresTables` state to the API call:

```javascript
response = await generateSparkCode(
  prompt, 
  sessionId, 
  s3InputPath, 
  selectedTables.length > 0 ? selectedTables : null,
  selectedPostgresTables.length > 0 ? selectedPostgresTables : null,  // ← ADDED
  executionEngine
);
```

### 3. Backend Response Enhancement (backend/main.py)
Added `execution_platform` to response for debugging:

```python
return {
    "success": True,
    "result": agent_result,
    "framework": FRAMEWORK_SPARK,
    "execution_platform": execution_platform  # ← ADDED
}
```

## Backend Routing Logic (Already Correct)
The backend correctly routes PostgreSQL requests to EMR at lines 1335-1336:

```python
if selected_tables_list or selected_postgres_tables:
    execution_platform = 'emr'
```

## Verification

### Automated Test
Run: `python test_postgres_e2e.py`

Expected output:
```
✅ TEST PASSED: PostgreSQL routed to EMR
```

### Manual Verification
Check backend logs for:
```
🔍 DEBUG - selected_postgres_tables: [...]
🔍 DEBUG - Routing to EMR (postgres=True, glue=False)
```

## Status
✅ **FIXED** - PostgreSQL workloads now correctly route to EMR Serverless
