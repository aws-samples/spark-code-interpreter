# Glue Table Support Enhancement

## Issue
The code generation agent was not properly recognizing and using Glue tables from the AWS Glue Data Catalog, only focusing on CSV files.

## Root Cause
The agent's system prompt didn't have explicit enough instructions on:
1. How to identify Glue tables in the prompt
2. How to use Glue table S3 locations with Ray
3. That Glue tables should be read with `ray.data.read_parquet()` instead of `read_csv()`

## Solution
Enhanced the code generation agent's system prompt with explicit instructions for handling both CSV files and Glue tables.

### Changes Made

**File:** `backend/agents.py`

**Enhanced System Prompt:**

```python
DATA SOURCES IN PROMPT:
The prompt will contain available data sources in this format:

CSV Files:
  Available CSV file:
    - Filename: sales.csv
    - S3 Path: s3://bucket/sessions/abc/csv/sales.csv

Glue Tables:
  Available Glue tables:
    - database_name.table_name at s3://bucket/path/to/data

RAY OPERATIONS:
- ray.data.read_csv(s3_path) - Read CSV from S3
- ray.data.read_parquet(s3_path) - Read Parquet from S3 (use for Glue tables)

CRITICAL RULES:
- For CSV files: Use exact S3 path from "S3 Path:" line
- For Glue tables: Use S3 location from "at s3://..." with ray.data.read_parquet()
```

## How It Works

### Backend Prompt Building (main.py)
```python
prompt_parts = [f"Session ID: {session_id}"]

if csv_data:
    prompt_parts.append(f"\nAvailable CSV file:")
    prompt_parts.append(f"  - Filename: {csv_data['filename']}")
    prompt_parts.append(f"  - S3 Path: {csv_data['s3_path']}")

if tables_data:
    prompt_parts.append(f"\nAvailable Glue tables:")
    for table in tables_data:
        prompt_parts.append(f"  - {table['database']}.{table['table']} at {table['location']}")

prompt_parts.append(f"\n{request.prompt}")
```

### Example Prompt Sent to Agent
```
Session ID: abc-123

Available CSV file:
  - Filename: sales.csv
  - S3 Path: s3://strands-ray-data/sessions/abc-123/csv/sales.csv

Available Glue tables:
  - northwind.customers at s3://my-data-lake/northwind/customers/
  - northwind.orders at s3://my-data-lake/northwind/orders/

Join the sales CSV with customer and order data
```

### Expected Generated Code
```python
import ray

ray.init()

# Read CSV file
sales_ds = ray.data.read_csv("s3://strands-ray-data/sessions/abc-123/csv/sales.csv")

# Read Glue tables (Parquet format)
customers_ds = ray.data.read_parquet("s3://my-data-lake/northwind/customers/")
orders_ds = ray.data.read_parquet("s3://my-data-lake/northwind/orders/")

# Join datasets
# ... rest of code
```

## Key Points

1. **CSV Files** → Use `ray.data.read_csv()` with S3 path from prompt
2. **Glue Tables** → Use `ray.data.read_parquet()` with S3 location from prompt
3. **Both data sources** are passed in the prompt text, not via tool calls
4. **Agent extracts** S3 paths directly from the formatted prompt

## Deployment

Code generation agent redeployed:
- Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9`
- Build: CodeBuild completed successfully
- Status: ✅ Deployed

## Testing

To test Glue table support:
1. Select tables from Glue Data Catalog in the UI
2. Generate code with a prompt like "Analyze the customer data"
3. Verify generated code uses `ray.data.read_parquet()` with correct S3 locations

## Summary

Enhanced the code generation agent's system prompt with explicit instructions for handling Glue tables. The agent now:
- Recognizes both CSV files and Glue tables in the prompt
- Uses appropriate Ray methods for each data source type
- Extracts S3 paths correctly from the formatted prompt text
