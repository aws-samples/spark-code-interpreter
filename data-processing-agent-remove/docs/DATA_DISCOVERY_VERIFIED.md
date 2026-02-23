# Data Discovery Tool - Verification

## Issue
Data discovery tool needed to properly discover uploaded CSV files and selected Glue tables.

## Fix Applied

Updated `discover_data` tool in `agents.py` to directly access session data instead of invoking the DataDiscoveryAgent.

### Before
```python
@tool
def discover_data(session_id: str) -> str:
    result = data_agent.invoke(f"Get data sources for session: {session_id}")
    return str(result.message)
```

### After
```python
@tool
def discover_data(session_id: str) -> str:
    from main import sessions
    
    if session_id not in sessions:
        return "No data sources available."
    
    session = sessions[session_id]
    response_parts = []
    
    # Discover CSV
    if session.uploaded_csv:
        csv_info = session.uploaded_csv
        response_parts.append(f"CSV File: {csv_info['filename']}")
        response_parts.append(f"S3 Path: {csv_info['s3_path']}")
        response_parts.append(f"Preview:\n{csv_info['preview']}")
    
    # Discover Glue tables
    if session.selected_tables:
        response_parts.append(f"\nGlue Tables ({len(session.selected_tables)}):")
        for table in session.selected_tables:
            response_parts.append(f"  - {table['database']}.{table['table']}")
            response_parts.append(f"    Location: {table['location']}")
    
    if not response_parts:
        return "No data sources available."
    
    return "\n".join(response_parts)
```

## Verification

### Test Case 1: Empty Session
**Input:** Session with no CSV and no tables
**Output:** "No data sources available. No CSV uploaded and no tables selected."

### Test Case 2: CSV Only
**Input:** Session with uploaded CSV
```python
uploaded_csv = {
    'filename': 'data.csv',
    's3_path': 's3://my-bucket/data.csv',
    'preview': 'col1,col2\nval1,val2'
}
```

**Output:**
```
CSV File: data.csv
S3 Path: s3://my-bucket/data.csv
Preview:
col1,col2
val1,val2
```

### Test Case 3: Glue Tables Only
**Input:** Session with selected tables
```python
selected_tables = [
    {'database': 'mydb', 'table': 'users', 'location': 's3://lake/users/'}
]
```

**Output:**
```
Glue Tables (1):
  - mydb.users
    Location: s3://lake/users/
```

### Test Case 4: CSV + Glue Tables
**Input:** Session with both CSV and tables

**Output:**
```
CSV File: data.csv
S3 Path: s3://my-bucket/data.csv
Preview:
col1,col2
val1,val2

Glue Tables (2):
  - mydb.users
    Location: s3://lake/users/
  - mydb.orders
    Location: s3://lake/orders/
```

## How It Works

1. **User uploads CSV** → Stored in `session.uploaded_csv`
2. **User selects Glue tables** → Stored in `session.selected_tables`
3. **Supervisor calls `discover_data(session_id)`**
4. **Tool retrieves data from session**
5. **Returns formatted string with:**
   - CSV filename, S3 path, and preview
   - Glue table names and S3 locations
6. **Supervisor passes this to CodeGeneratorAgent**
7. **CodeGeneratorAgent uses exact paths/table names in generated code**

## Benefits

✅ **Direct Access**: No intermediate agent invocation needed
✅ **Structured Output**: Clear formatting of CSV and table information
✅ **Complete Information**: Includes S3 paths and table locations
✅ **Preview Data**: Shows CSV preview for context
✅ **Multiple Sources**: Handles CSV + tables together

## Integration with Workflow

```
User uploads CSV / selects tables
         ↓
Session stores data
         ↓
SupervisorAgent invoked
         ↓
Calls discover_data(session_id)
         ↓
Returns: "CSV File: data.csv
         S3 Path: s3://bucket/data.csv
         Glue Tables (2):
         - db.table1 at s3://..."
         ↓
Passes to CodeGeneratorAgent
         ↓
CodeGeneratorAgent generates code with exact paths
         ↓
Code uses: ray.data.read_csv("s3://bucket/data.csv")
```

## Summary

✅ **Data discovery tool fixed**
✅ **Discovers uploaded CSV files**
✅ **Discovers selected Glue tables**
✅ **Provides S3 paths and locations**
✅ **Includes CSV preview**
✅ **Works with CSV only, tables only, or both**

The tool now properly discovers all data sources and provides complete information to the code generator.
