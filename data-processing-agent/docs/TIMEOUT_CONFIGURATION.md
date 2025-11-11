# Timeout Configuration for EMR Workloads

## Overview
EMR Serverless jobs require significantly longer timeouts than Lambda due to cold start and execution time.

---

## Timeout Hierarchy

```
Client Request Timeout (900s)
    ↓
Asyncio Timeout (1260s = 21 min)
    ↓
Boto3 Read Timeout (1200s = 20 min)
    ↓
EMR Job Execution (varies)
```

**Rule:** Each layer must have longer timeout than the layer below to avoid premature cancellation.

---

## Configuration Changes

### 1. Backend API (backend/main.py)

#### Generate Endpoint (Line 1222)
```python
spark_client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1',
    config=boto3.session.Config(
        read_timeout=1200,  # 20 minutes - allows for EMR cold start + execution
        connect_timeout=30,
        retries={'max_attempts': 0}
    )
)
```

#### Generate Endpoint Asyncio (Line 1377)
```python
result = await asyncio.wait_for(
    asyncio.get_event_loop().run_in_executor(
        None, invoke_spark_agent, payload, session_id, attempt
    ),
    timeout=1260  # 21 minute timeout (boto3 times out first at 20 min)
)
```

#### Execute Endpoint (Line 1460)
```python
spark_client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1',
    config=boto3.session.Config(
        read_timeout=1200,  # 20 minutes for EMR workloads
        connect_timeout=30,
        retries={'max_attempts': 0}
    )
)
```

### 2. Client Request Timeout

**Test Scripts:**
```python
response = requests.post(
    f"{BACKEND_URL}/spark/generate",
    json=payload,
    timeout=900  # 15 minutes minimum for EMR
)
```

**Recommended:** 900-1800 seconds (15-30 minutes) for EMR workloads

---

## Timeout Breakdown by Platform

### Lambda Execution
- **Typical Duration:** 10-60 seconds
- **Boto3 Read Timeout:** 1200s (sufficient)
- **Asyncio Timeout:** 1260s (sufficient)
- **Client Timeout:** 900s (sufficient)

### EMR Execution
- **Cold Start:** 1-3 minutes (if app stopped)
- **Job Scheduling:** 30-60 seconds
- **Job Execution:** 2-15 minutes (depends on data size)
- **Total:** 3-20 minutes
- **Boto3 Read Timeout:** 1200s (20 min) ✅
- **Asyncio Timeout:** 1260s (21 min) ✅
- **Client Timeout:** 900s (15 min) - may need increase for large jobs

---

## Settings Configuration

### Backend Settings (backend/settings.json)

```json
{
  "spark": {
    "lambda_timeout_seconds": 300,
    "emr_timeout_minutes": 10
  }
}
```

**Note:** These are internal EMR job timeouts, not the API client timeouts.

---

## Troubleshooting

### Symptom: "Read timeout on endpoint URL"

**Cause:** Boto3 client timeout too short for EMR job duration

**Solution:**
1. Check EMR job actual duration
2. Increase `read_timeout` in boto3 client config
3. Ensure asyncio timeout > boto3 timeout
4. Ensure client request timeout > asyncio timeout

### Symptom: "Agent timed out" after asyncio.TimeoutError

**Cause:** Asyncio timeout too short

**Solution:**
1. Increase `timeout` parameter in `asyncio.wait_for()`
2. Ensure it's longer than boto3 read_timeout

### Symptom: Request hangs indefinitely

**Cause:** No timeout set on client request

**Solution:**
```python
response = requests.post(url, json=payload, timeout=900)
```

---

## Recommended Timeout Values

### Development/Testing
```python
# Backend boto3 client
read_timeout = 1200  # 20 minutes

# Backend asyncio
asyncio_timeout = 1260  # 21 minutes

# Client request
request_timeout = 900  # 15 minutes
```

### Production (Large Datasets)
```python
# Backend boto3 client
read_timeout = 1800  # 30 minutes

# Backend asyncio
asyncio_timeout = 1860  # 31 minutes

# Client request
request_timeout = 1500  # 25 minutes
```

---

## Code Locations

**Backend API Timeouts:**
- `/spark/generate` endpoint: Line 1222 (boto3), Line 1377 (asyncio)
- `/spark/execute` endpoint: Line 1460 (boto3)

**Test Scripts:**
- `test_pg_clean.py`: Line with `timeout=900`
- `test_pg_final_validation.py`: Line with `timeout=720` (should be 900+)

---

## Verification

```bash
# Check current timeout configuration
grep -n "read_timeout" backend/main.py | grep -E "(1200|600)"
grep -n "timeout=" backend/main.py | grep -E "(1260|720)"
```

**Expected Output:**
- `read_timeout=1200` (20 minutes)
- `timeout=1260` (21 minutes)

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-04  
**Status:** ✅ Configured for EMR Workloads
