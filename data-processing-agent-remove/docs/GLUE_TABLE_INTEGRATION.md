# Glue Table Integration Summary

## Current Implementation

### Backend Endpoints (main.py)
- `GET /glue/databases` - Lists all Glue databases
- `GET /glue/tables/{database}` - Lists tables in a database with basic schema (first 5 columns)
- `POST /sessions/{session_id}/select-tables` - Stores selected tables for a session

### Frontend
- GlueTableSelector component allows users to browse and select tables
- Selected tables are passed to the Spark generation endpoint via `selected_tables` parameter

### Spark Supervisor Agent Tools

#### New Tool Added: `fetch_glue_table_schema`
**Purpose**: Fetch complete table schema from Glue Data Catalog

**Parameters**:
- `database_name`: Glue database name
- `table_name`: Glue table name

**Returns**:
```json
{
  "status": "success",
  "database": "my_database",
  "table": "my_table",
  "location": "s3://bucket/path/",
  "input_format": "org.apache.hadoop.mapred.TextInputFormat",
  "output_format": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
  "columns": [
    {"name": "col1", "type": "string", "comment": ""},
    {"name": "col2", "type": "int", "comment": ""}
  ],
  "partition_keys": [
    {"name": "year", "type": "int"},
    {"name": "month", "type": "int"}
  ],
  "table_type": "EXTERNAL_TABLE",
  "parameters": {}
}
```

## Updated Workflow

### When User Selects Glue Tables:

1. **Frontend**: User selects tables from GlueTableSelector
2. **Backend**: Stores selected tables in session
3. **Agent Invocation**: `selected_tables` passed to spark_supervisor_agent
4. **Agent Workflow**:
   - Step 1: For each selected table, call `fetch_glue_table_schema` to get complete schema
   - Step 2: Pass table schemas to `call_code_generation_agent` 
   - Step 3-8: Continue with normal workflow (extract, validate, execute, fetch results)

### Generated Code Pattern

The agent will generate Spark SQL code like:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("GlueTableQuery") \
    .enableHiveSupport() \
    .getOrCreate()

# Query Glue table using Spark SQL
df = spark.sql("""
    SELECT col1, col2, COUNT(*) as count
    FROM my_database.my_table
    WHERE year = 2024
    GROUP BY col1, col2
""")

# Write results to S3
df.coalesce(1).write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("s3://bucket/output/session-id")
```

## Key Features

1. **Schema-Aware Code Generation**: Agent has access to complete table schema (columns, types, partitions)
2. **Spark SQL Support**: Generated code uses Spark SQL to query Glue tables
3. **Hive Metastore Integration**: Spark session enables Hive support to access Glue catalog
4. **Same Execution Flow**: Lambda and EMR both support Glue table queries
5. **Formatted Output**: Results displayed in formatted table in Outputs section

## Testing

To test Glue table integration:

```python
import requests

payload = {
    "prompt": "Show me the top 10 rows from the sales table",
    "session_id": "test-glue-session",
    "selected_tables": ["my_database.sales_table"],
    "execution_engine": "lambda"  # or "emr"
}

response = requests.post(
    "http://localhost:8000/spark/generate",
    json=payload
)
```

## Notes

- The `fetch_glue_table_schema` tool is called automatically by the agent when `selected_tables` are provided
- Table schemas are passed to the code generation agent for context-aware code generation
- Both Lambda and EMR execution platforms support Glue table queries via Spark SQL
- Results are written to S3 and displayed in the formatted Outputs section
