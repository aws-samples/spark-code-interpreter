# Fetch Spark Results Fix

## Problem
EMR executions were showing stale placeholder data `[{"0": "id", "1": "name"}]` in the Output section instead of actual results or empty array.

## Root Cause
1. **Stale Data in S3:** The base S3 output path (`s3://spark-data-260005718447-us-east-1/output/`) contained old CSV files from previous executions
2. **No Output Written:** When Spark code only displays data (`.show()`) without writing to S3 (`.write`), no new files are created
3. **fetch_spark_results Reading Old Files:** The function was reading ALL CSV files in the output path, including stale ones from hours/days ago

## Investigation
- Checked CloudWatch logs confirming `fetch_spark_results` was being called correctly
- Found the tool was returning data successfully: `'data': [{'Date': '2024-12-26...', ...}]`
- But agent's final response had: `"actual_results": [{"0": "id", "1": "name"}]`
- Discovered the S3 output path had a file `part-00000-4da9d76e-924a-4c7b-bd93-1e1f4a6d6114-c000.csv` containing only `id,name`
- This file was from a previous test and was being read instead of new execution output

## Solution
Updated `fetch_spark_results` function to only read CSV files modified within the last 5 minutes:

```python
# List CSV files modified in last 5 minutes (recent execution)
response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
csv_files = [(obj['Key'], obj['LastModified']) for obj in response.get('Contents', []) 
             if obj['Key'].endswith('.csv') and not obj['Key'].endswith('_SUCCESS')
             and obj['LastModified'] > cutoff_time]

if not csv_files:
    return {
        'status': 'success',
        'data': [],
        'row_count': 0,
        'message': 'No recent CSV files found in output path'
    }

# Sort by modification time, get most recent
csv_files.sort(key=lambda x: x[1], reverse=True)
most_recent_file = csv_files[0][0]
```

## Changes Made
1. Added timestamp filtering to only read files modified in last 5 minutes
2. Sort files by modification time and use the most recent one
3. Return empty `data: []` when no recent files found
4. Updated file references to use `most_recent_file` variable

## Testing Results

### Before Fix
```json
{
  "success": true,
  "execution_result": "success",
  "actual_results": [{"0": "id", "1": "name"}]  // Stale data
}
```

### After Fix
```json
{
  "success": true,
  "execution_result": "success",
  "actual_results": []  // Correct empty array when no output written
}
```

## Behavior
- **Code writes to S3:** Returns actual data from the most recent CSV file
- **Code only displays (no write):** Returns empty array `[]`
- **Old cached files:** Ignored if older than 5 minutes
- **Multiple files:** Uses the most recently modified file

## Files Modified
- `backend/spark-supervisor-agent/spark_supervisor_agent.py` - Updated `fetch_spark_results` function

## Deployment
```bash
cd backend/spark-supervisor-agent
conda run -n bedrock-sdk python agent_deployment.py
```

## Impact
- ✅ EMR executions now show correct empty results when code doesn't write output
- ✅ Lambda executions show correct empty results when code doesn't write output  
- ✅ Stale cached data no longer pollutes new execution results
- ✅ When code DOES write output, most recent file is used
- ✅ No breaking changes to existing functionality
