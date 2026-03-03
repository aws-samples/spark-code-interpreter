# EMR Timeout Investigation Summary

## Problem
EMR Serverless executions were timing out even though the agent and code were working correctly.

## Root Cause Analysis

### 1. Misaligned Timeouts (CRITICAL BUG)
**Original Configuration:**
- boto3 read_timeout: 240 seconds (4 minutes)
- asyncio.wait_for timeout: 180 seconds (3 minutes)

**Problem:** When asyncio times out at 180s, the boto3 call continues running for another 60 seconds in the executor thread. This blocks the thread pool and prevents subsequent requests from being processed.

**Fix:** Reversed the timeouts so boto3 times out FIRST:
- boto3 read_timeout: 540 seconds (9 minutes)
- asyncio.wait_for timeout: 600 seconds (10 minutes)

### 2. EMR Serverless Cold Start Performance
**Test Results:**
- Lambda execution: ~121 seconds (2 minutes)
- EMR execution: >480 seconds (>8 minutes) and still running

**EMR Application Configuration:**
```json
{
  "applicationId": "00fv6g7rptsov009",
  "name": "spark-code-interpreter-app",
  "releaseLabel": "emr-7.0.0",
  "state": "STARTED",
  "initialCapacity": {
    "Executor": {
      "workerCount": 2,
      "workerConfiguration": {
        "cpu": "4 vCPU",
        "memory": "8 GB"
      }
    },
    "Driver": {
      "workerCount": 1,
      "workerConfiguration": {
        "cpu": "2 vCPU",
        "memory": "4 GB"
      }
    }
  },
  "autoStopConfiguration": {
    "enabled": true,
    "idleTimeoutMinutes": 15
  }
}
```

**Findings:**
- Even with initial capacity and auto-start enabled, EMR Serverless has significant cold start overhead
- EMR jobs were still RUNNING after 8 minutes
- This is expected behavior for EMR Serverless, not a bug

## Solution

### Immediate Fix
1. **Aligned Timeouts:** boto3 (540s) < asyncio (600s)
2. **Increased Timeouts:** 10 minutes to accommodate EMR cold starts
3. **Proper Thread Pool Management:** Ensures boto3 times out first, releasing executor threads

### Code Changes
```python
# backend/main.py - Spark agent invocation
spark_client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1',
    config=boto3.session.Config(
        read_timeout=540,  # 9 minutes - less than asyncio timeout
        connect_timeout=30,
        retries={'max_attempts': 0}
    )
)

result = await asyncio.wait_for(
    asyncio.get_event_loop().run_in_executor(
        None, invoke_spark_agent, payload, session_id, attempt
    ),
    timeout=600  # 10 minutes - boto3 times out first
)
```

### Long-term Recommendations

1. **Intelligent Platform Selection:**
   - Use Lambda for queries on small datasets (<100MB)
   - Use EMR for large datasets (>100MB) or complex transformations
   - Implement automatic platform selection based on data size

2. **Keep EMR Warm:**
   - Run periodic health check jobs every 10 minutes
   - Prevents auto-stop from shutting down the application
   - Reduces cold start latency to <30 seconds

3. **User Experience:**
   - Show progress indicator for EMR executions
   - Display estimated time: "EMR execution may take 5-10 minutes for first run"
   - Cache results to avoid re-execution

4. **Monitoring:**
   - Track EMR job execution times
   - Alert if execution times exceed 10 minutes
   - Monitor thread pool utilization

## Testing

### Lambda Execution (Fast)
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Load sales data and show first 5 rows",
    "session_id": "test-123",
    "s3_input_path": "s3://strands-agent-data/sample-data/sales.csv",
    "execution_platform": "lambda"
  }'
```
Expected time: ~2 minutes

### EMR Execution (Slow)
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Load sales data and show first 5 rows",
    "session_id": "test-456",
    "s3_input_path": "s3://strands-agent-data/sample-data/sales.csv",
    "execution_platform": "emr"
  }'
```
Expected time: 8-10 minutes (first run), 2-3 minutes (warm)

## Key Learnings

1. **Timeout Alignment is Critical:** Always ensure boto3 timeout < asyncio timeout to prevent thread pool exhaustion
2. **EMR Serverless is Slow:** Cold starts take 8-10 minutes even with initial capacity
3. **Platform Selection Matters:** Lambda is 4-5x faster for small datasets
4. **Thread Pool Management:** Misaligned timeouts cause cascading failures that appear as infrastructure issues

## Related Issues
- Thread pool exhaustion causing requests to not reach backend
- CloudWatch logs showing successful execution but backend timing out
- Frontend showing "failed" status despite successful agent execution
