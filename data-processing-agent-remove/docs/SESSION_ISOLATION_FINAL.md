# Session Isolation - Final Implementation

## Design

**CSV and tables can coexist** - both can be selected for the same prompt.

**Clearing happens ONLY after code execution** - ensures data sources from one prompt are not used in the next.

## How It Works

### 1. Data Source Selection (No Clearing)

```
Upload CSV        → session.uploaded_csv = {data}
                    session.selected_tables = [existing]  ✅ PRESERVED

Select Tables     → session.selected_tables = [tables]
                    session.uploaded_csv = {existing}     ✅ PRESERVED
```

**Both can be selected for the same prompt.**

### 2. Code Generation

Agent discovers ALL available data sources:
```python
@tool
def get_data_sources(session_id: str) -> dict:
    return {
        "csv": session.uploaded_csv,      # Can be present
        "tables": session.selected_tables  # Can be present
    }
```

Agent generates code using whatever is available:
- CSV only
- Tables only  
- **Both CSV and tables** ✅

### 3. After Execution (Clearing)

```python
# Backend (main.py)
session.uploaded_csv = None
session.selected_tables = []
print(f"🧹 Cleared session data sources")
```

```javascript
// Frontend (App.jsx)
setUploadedCsv(null);
setSelectedTables([]);
setResetKey(prev => prev + 1);
```

**Both cleared after execution** - next prompt starts fresh.

## Session Lifecycle

### Example: Using Both CSV and Tables

```
1. Upload CSV
   → session.uploaded_csv = {data}
   → session.selected_tables = []

2. Select Tables
   → session.uploaded_csv = {data}      ✅ STILL PRESENT
   → session.selected_tables = [tables] ✅ ADDED

3. Generate Code
   → Agent sees BOTH CSV and tables
   → Generates code using both data sources

4. Execute Code
   → Code runs successfully
   → session.uploaded_csv = None        ✅ CLEARED
   → session.selected_tables = []       ✅ CLEARED

5. Next Prompt
   → Clean slate
   → Must upload/select data sources again
```

### Example: CSV Only

```
1. Upload CSV
   → session.uploaded_csv = {data}

2. Generate Code
   → Agent sees CSV only
   → Generates code using CSV

3. Execute Code
   → session.uploaded_csv = None  ✅ CLEARED
```

### Example: Tables Only

```
1. Select Tables
   → session.selected_tables = [tables]

2. Generate Code
   → Agent sees tables only
   → Generates code using tables

3. Execute Code
   → session.selected_tables = []  ✅ CLEARED
```

## Code Locations

### Backend Clearing (main.py)

**After execution** (lines 204-207):
```python
# Clear data sources for session isolation
session.uploaded_csv = None
session.selected_tables = []
print(f"🧹 Cleared session data sources")
```

### Frontend Clearing (App.jsx)

**After auto-execution** (lines 106-109):
```javascript
// Clear data sources for session isolation
setUploadedCsv(null);
setSelectedTables([]);
setResetKey(prev => prev + 1);
```

## Session State Tracking

Backend logs show session state:
```
📊 Session state before generation:
   - CSV: filename.csv (or None)
   - Tables: 2 selected (or 0)

🧹 Cleared session data sources (CSV was: filename.csv or None)
```

## Use Cases Supported

✅ **CSV only**: Upload CSV, generate code
✅ **Tables only**: Select tables, generate code
✅ **Both CSV and tables**: Upload CSV + select tables, generate code using both
✅ **Session isolation**: After execution, both cleared for next prompt

## Testing

### Test 1: Both CSV and Tables
```
1. Upload CSV file
2. Select Glue tables
3. Generate code
   → Should use BOTH CSV and tables
4. After execution
   → Both should be cleared
5. Generate new code
   → Should prompt to select data sources
```

### Test 2: Sequential Prompts
```
1. Upload CSV, generate code, execute
   → CSV cleared after execution
2. Select tables, generate code, execute
   → Tables cleared after execution
3. Each prompt uses only its own data sources
```

## Summary

✅ **Flexible**: CSV and tables can coexist
✅ **Isolated**: Cleared after each execution
✅ **Clean**: Each prompt starts fresh
✅ **Preserved**: Session history maintained

The implementation supports all use cases:
- Single data source (CSV or tables)
- Multiple data sources (CSV + tables)
- Proper isolation between prompts
