# New S3 Structure - Session-Based Organization

## Overview

All data is now organized under a single bucket with session-based folders for clean organization.

---

## S3 Structure

```
s3://spark-data-817323390093-us-east-1/
├── {session-id-1}/
│   ├── scripts/
│   │   └── {session-id-1}_code.py
│   └── output/
│       └── (execution results)
├── {session-id-2}/
│   ├── scripts/
│   │   └── {session-id-2}_code.py
│   └── output/
│       └── (execution results)
└── {session-id-3}/
    ├── scripts/
    │   └── {session-id-3}_code.py
    └── output/
        └── (execution results)
```

---

## Benefits

1. **Single Bucket** - All data in one place
2. **Session Isolation** - Each query gets its own folder
3. **Organized** - Clear separation between code and results
4. **Traceable** - Session ID links request to results
5. **Clean** - Easy to find and manage data

---

## What's Stored

### Scripts Folder
**Path:** `s3://spark-data-817323390093-us-east-1/{session-id}/scripts/`

**Contains:**
- Generated PySpark code
- File name: `{session-id}_code.py`

**Example:**
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("SimpleCalculation").getOrCreate()
df = spark.createDataFrame([(5 + 5,)], ["result"])
df.show()
df.write.mode("overwrite").csv("s3://spark-data-817323390093-us-east-1/{session-id}/output/")
spark.stop()
```

### Output Folder
**Path:** `s3://spark-data-817323390093-us-east-1/{session-id}/output/`

**Contains:**
- Execution results (CSV, Parquet, etc.)
- Query output data
- Generated visualizations (if any)

---

## Configuration

The wrapper Lambda now passes this configuration to the agent:

```python
{
    'session_id': '{uuid}',
    's3_output_path': 's3://spark-data-817323390093-us-east-1/{session-id}/output/',
    'config': {
        's3_bucket': 'spark-data-817323390093-us-east-1',
        's3_output_path': 's3://spark-data-817323390093-us-east-1/{session-id}/output/',
        # ... other config
    }
}
```

The agent uses this to:
1. Save generated code to `{session-id}/scripts/`
2. Configure Spark to write results to `{session-id}/output/`

---

## Testing

### Run Test Script
```bash
cd scripts
./test-s3-structure.sh
```

This will:
1. Invoke the Lambda with a test query
2. Wait for completion (~60 seconds)
3. Extract the session ID
4. Check S3 for the session folder
5. Display the generated code and results

### Manual Test
```bash
# Invoke Lambda
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"what is 5+5"}' \
  /tmp/response.json

# Get session ID
SESSION_ID=$(cat /tmp/response.json | jq -r '.body' | jq -r '.sessionId')

# Check S3
aws s3 ls s3://spark-data-817323390093-us-east-1/$SESSION_ID/ --recursive --human-readable

# Download generated code
aws s3 cp s3://spark-data-817323390093-us-east-1/$SESSION_ID/scripts/${SESSION_ID}_code.py -

# Check results
aws s3 ls s3://spark-data-817323390093-us-east-1/$SESSION_ID/output/ --recursive
```

---

## Finding Results

### By Session ID
If you know the session ID from the Lambda response:

```bash
SESSION_ID="abc123-def456-..."
aws s3 ls s3://spark-data-817323390093-us-east-1/$SESSION_ID/ --recursive
```

### Recent Sessions
List the most recent sessions:

```bash
aws s3 ls s3://spark-data-817323390093-us-east-1/ | tail -10
```

### All Results
List everything:

```bash
aws s3 ls s3://spark-data-817323390093-us-east-1/ --recursive --human-readable | tail -50
```

---

## Lambda Response Format

The Lambda returns the session ID so you can find the results:

```json
{
  "statusCode": 200,
  "body": {
    "result": "{...agent response...}",
    "prompt": "what is 5+5",
    "sessionId": "abc123-def456-ghi789"
  }
}
```

Use the `sessionId` to locate the data in S3:
- Code: `s3://spark-data-817323390093-us-east-1/{sessionId}/scripts/`
- Results: `s3://spark-data-817323390093-us-east-1/{sessionId}/output/`

---

## Cleanup

To clean up old sessions:

```bash
# List sessions older than 7 days
aws s3 ls s3://spark-data-817323390093-us-east-1/ \
  | awk '{print $2}' \
  | while read session; do
      aws s3 ls s3://spark-data-817323390093-us-east-1/$session --recursive \
        | awk '$1 < "'$(date -d '7 days ago' +%Y-%m-%d)'" {print}'
    done

# Delete old sessions (be careful!)
# aws s3 rm s3://spark-data-817323390093-us-east-1/{old-session-id}/ --recursive
```

Or set up S3 lifecycle policies to auto-delete old data.

---

## Example Workflow

1. **User asks question:**
   ```
   "Calculate average sales by region"
   ```

2. **Lambda invokes agent:**
   - Session ID: `f47ac10b-58cc-4372-a567-0e02b2c3d479`

3. **Agent generates code:**
   - Saved to: `s3://spark-data-817323390093-us-east-1/f47ac10b-58cc-4372-a567-0e02b2c3d479/scripts/f47ac10b-58cc-4372-a567-0e02b2c3d479_code.py`

4. **Agent executes code:**
   - Results written to: `s3://spark-data-817323390093-us-east-1/f47ac10b-58cc-4372-a567-0e02b2c3d479/output/`

5. **User retrieves results:**
   ```bash
   aws s3 ls s3://spark-data-817323390093-us-east-1/f47ac10b-58cc-4372-a567-0e02b2c3d479/output/
   ```

---

## Summary

**Single Bucket:** `s3://spark-data-817323390093-us-east-1`

**Structure:** `{session-id}/scripts/` and `{session-id}/output/`

**Benefits:** Clean, organized, traceable, easy to manage

**Test:** Run `./test-s3-structure.sh` to verify everything works!
