# Auto Platform Selection Feature

## Overview

Added intelligent auto-selection of execution platform (Lambda vs EMR) based on file size thresholds.

## New Tool: `select_execution_platform`

```python
@tool
def select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0) -> str:
    """Intelligently select execution platform based on file size threshold"""
```

### Selection Logic

1. **File size provided** (`file_size_mb > 0`):
   - Compare against threshold (default: 500MB)
   - Return 'lambda' if ≤ threshold
   - Return 'emr' if > threshold

2. **S3 path provided** (`s3_input_path`):
   - Call `s3_client.head_object()` to get file size
   - Convert ContentLength to MB
   - Compare against threshold
   - Return 'lambda' or 'emr'

3. **No size information**:
   - Default to 'lambda' (faster startup)

### Configuration

Threshold is configurable via runtime config:
```python
config = {
    "file_size_threshold_mb": 500  # Default: 500MB
}
```

## Usage

### Backend passes `execution_platform: 'auto'`

The agent will:
1. Call `select_execution_platform(s3_input_path, file_size_mb)`
2. Get returned platform ('lambda' or 'emr')
3. Use that platform for execution

### Example Workflow

**Small file (< 500MB):**
```
execution_platform = 'auto'
s3_input_path = 's3://bucket/small-data.csv'  # 100MB

→ select_execution_platform() returns 'lambda'
→ execute_spark_code_lambda() is called
```

**Large file (> 500MB):**
```
execution_platform = 'auto'
file_size_mb = 1000

→ select_execution_platform() returns 'emr'
→ execute_spark_code_emr() is called
```

**Unknown size:**
```
execution_platform = 'auto'
# No s3_input_path or file_size_mb provided

→ select_execution_platform() returns 'lambda' (default)
→ execute_spark_code_lambda() is called
```

## System Prompt Updates

### GENERATE REQUEST WORKFLOW

Added Step 0:
```
0. PLATFORM SELECTION: If execution_platform == 'auto':
   - Call select_execution_platform(s3_input_path, file_size_mb) to determine platform
   - Use returned platform ('lambda' or 'emr') for subsequent steps
   - Log: "Auto-selected execution platform: {platform} (file size: {size}MB, threshold: {threshold}MB)"
```

### EXECUTE REQUEST WORKFLOW

Added Step 0:
```
0. PLATFORM SELECTION: If execution_platform == 'auto':
   - Call select_execution_platform(s3_input_path, file_size_mb) to determine platform
   - Use returned platform ('lambda' or 'emr') for subsequent steps
   - Log: "Auto-selected execution platform: {platform}"
```

## Supported Values for `execution_platform`

1. **'lambda'**: Always use Lambda (explicit)
2. **'emr'**: Always use EMR (explicit)
3. **'auto'**: Intelligent selection based on file size (NEW)

## Benefits

✅ **Automatic optimization**: Right platform for the data size  
✅ **Cost efficient**: Lambda for small files, EMR for large  
✅ **Performance**: Faster startup for small jobs, scalable for large  
✅ **No manual decision**: Backend doesn't need to decide  
✅ **Configurable**: Threshold can be adjusted per deployment  

## Testing

```python
# Test auto selection with small file
payload = {
    "prompt": "Analyze sales data",
    "execution_platform": "auto",
    "s3_input_path": "s3://bucket/sales-100mb.csv",
    "s3_output_path": "s3://bucket/output/",
    "session_id": "test-123"
}
# Expected: Selects Lambda

# Test auto selection with large file
payload = {
    "prompt": "Analyze sales data",
    "execution_platform": "auto",
    "file_size_mb": 1000,
    "s3_output_path": "s3://bucket/output/",
    "session_id": "test-456"
}
# Expected: Selects EMR

# Test auto selection with unknown size
payload = {
    "prompt": "Generate sample data",
    "execution_platform": "auto",
    "s3_output_path": "s3://bucket/output/",
    "session_id": "test-789"
}
# Expected: Defaults to Lambda
```

## Deployment

```bash
conda activate bedrock-sdk
cd backend/spark-supervisor-agent
python agent_deployment.py
```

## No Breaking Changes

- Existing 'lambda' and 'emr' values still work
- 'auto' is a new optional value
- Default behavior unchanged if not using 'auto'
