# Fix for 422 Unprocessable Entity Error with Glue Tables

## Problem
When selecting Glue tables in the UI and clicking "Generate Code", the request failed with:
- HTTP 422 Unprocessable Entity
- Error: "Failed to generate Spark code"

## Root Cause
**Type mismatch between frontend and backend:**

**Frontend** sends:
```json
{
  "selected_tables": [
    {"database": "my_db", "table": "my_table"}
  ]
}
```

**Backend** expected:
```python
selected_tables: Optional[List[str]] = None  # List of strings
```

FastAPI validation rejected the request because it received objects instead of strings.

## Solution

### 1. Updated Backend Model
Added `TableReference` model and updated `SparkGenerateRequest`:

```python
class TableReference(BaseModel):
    database: str
    table: str

class SparkGenerateRequest(BaseModel):
    prompt: str
    session_id: str
    framework: str = FRAMEWORK_SPARK
    s3_input_path: Optional[str] = None
    selected_tables: Optional[List[TableReference]] = None  # Now accepts objects
    execution_platform: str = "lambda"
    execution_engine: str = "auto"
```

### 2. Convert Format for Agent
The agent expects `["database.table"]` format, so we convert:

```python
# Convert selected_tables from objects to "database.table" strings
selected_tables_list = None
if request.selected_tables:
    selected_tables_list = [f"{t.database}.{t.table}" for t in request.selected_tables]

payload = {
    "selected_tables": selected_tables_list,
    # ...
}
```

## Testing
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Show me the data",
    "session_id": "test",
    "selected_tables": [{"database": "db", "table": "tbl"}],
    "execution_engine": "lambda"
  }'
```

## Files Changed
- `backend/main.py`: Added `TableReference` model and conversion logic

## Status
✅ Fixed - Backend now accepts table objects from frontend and converts them for the agent
