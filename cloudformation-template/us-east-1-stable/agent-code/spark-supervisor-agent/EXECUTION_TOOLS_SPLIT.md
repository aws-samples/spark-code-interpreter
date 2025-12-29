# Spark Supervisor Agent - Execution Tools Split

## Change Summary

Split the single `execute_spark_code` tool into two separate tools for Lambda and EMR execution, plus added intelligent auto-selection based on file size.

## Changes Made

### 1. New Tools Created

#### `select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0) -> str`
- **Purpose**: Intelligently select execution platform based on file size threshold
- **Parameters**:
  - `s3_input_path`: S3 path to input file (optional, for size detection)
  - `file_size_mb`: File size in MB if known
- **Returns**: Selected platform ('lambda' or 'emr')
- **Logic**:
  - If file_size_mb provided: Use threshold comparison
  - If s3_input_path provided: Detect file size from S3
  - Default threshold: 500MB (configurable via runtime config)
  - Default to 'lambda' if size unknown

#### `execute_spark_code_lambda(spark_code: str, s3_output_path: str) -> dict`
- **Purpose**: Execute validated Spark code on AWS Lambda
- **Parameters**:
  - `spark_code`: Validated Spark code to execute
  - `s3_output_path`: S3 path for output results
- **Returns**: Execution result with Lambda-specific status
- **Key Features**:
  - Saves code to S3 for backend retrieval
  - Invokes Lambda function with RequestResponse
  - Returns status based on Lambda execution result

#### `execute_spark_code_emr(spark_code: str, s3_output_path: str) -> dict`
- **Purpose**: Execute validated Spark code on EMR Serverless
- **Parameters**:
  - `spark_code`: Validated Spark code to execute
  - `s3_output_path`: S3 path for output results
- **Returns**: Execution result with EMR-specific status
- **Key Features**:
  - Saves code to S3 for backend retrieval
  - Uploads script to S3 for EMR execution
  - Starts EMR Serverless job
  - Polls for job completion with timeout
  - Returns job state (SUCCESS/FAILED/CANCELLED)

### 2. System Prompt Updates

Updated the agent's system prompt to handle 'auto' platform selection:

**GENERATE REQUEST WORKFLOW (Step 0):**
```
0. PLATFORM SELECTION: If execution_platform == 'auto':
   - Call select_execution_platform(s3_input_path, file_size_mb) to determine platform
   - Use returned platform ('lambda' or 'emr') for subsequent steps
   - Log: "Auto-selected execution platform: {platform} (file size: {size}MB, threshold: {threshold}MB)"
```

**EXECUTE REQUEST WORKFLOW (Step 0):**
```
0. PLATFORM SELECTION: If execution_platform == 'auto':
   - Call select_execution_platform(s3_input_path, file_size_mb) to determine platform
   - Use returned platform ('lambda' or 'emr') for subsequent steps
   - Log: "Auto-selected execution platform: {platform}"
```

### 3. Agent Tools List Updated

```python
agent = Agent(
    model=model,
    system_prompt=system_prompt,
    tools=[
        select_execution_platform,      # NEW - Auto platform selection
        fetch_glue_table_schema, 
        call_code_generation_agent, 
        extract_python_code, 
        validate_spark_code, 
        execute_spark_code_lambda,      # NEW - Lambda execution
        execute_spark_code_emr,          # NEW - EMR execution
        extract_execution_logs, 
        fetch_spark_results
    ],
    name="SparkSupervisorAgent"
)
```

### 4. Context Building Updated

Updated the invoke function to mention auto platform selection:

**Execute-only mode:**
```python
context = f"""...
- If execution_platform == 'auto': Call select_execution_platform to determine platform
- Call the appropriate execution tool based on platform:
  * If platform == 'lambda': Call execute_spark_code_lambda(spark_code, s3_output_path)
  * If platform == 'emr': Call execute_spark_code_emr(spark_code, s3_output_path)
..."""
```

**Generate mode:**
```python
context = f"""...
If execution_platform is 'auto', call select_execution_platform first to determine the best platform.
Generate Spark code, validate it, execute it using the appropriate tool 
(execute_spark_code_lambda or execute_spark_code_emr based on selected platform), 
and return results.
..."""
```

## Platform Selection Logic

### Auto Selection Algorithm

1. **File size provided**: Compare against threshold (default 500MB)
   - `file_size_mb <= 500MB` → Lambda
   - `file_size_mb > 500MB` → EMR

2. **S3 path provided**: Detect file size from S3
   - Call `s3_client.head_object()` to get ContentLength
   - Convert to MB and compare against threshold

3. **No size info**: Default to Lambda (faster startup)

### Configuration

The threshold is configurable via runtime config:
```python
config = {
    "file_size_threshold_mb": 500  # Adjust as needed
}
```

## Benefits

1. **Intelligent Selection**: Automatically chooses optimal platform based on data size
2. **Clear Separation**: Each execution platform has its own dedicated tool
3. **No Fallback Logic**: Removed complex fallback logic from single tool
4. **Explicit Control**: Agent explicitly chooses which tool to call
5. **Simpler Code**: Each tool is focused on one execution platform
6. **Better Debugging**: Easier to trace which execution path was taken
7. **Maintainability**: Changes to Lambda or EMR execution are isolated

## Behavior

### Platform Selection Modes

1. **'lambda'**: Always use Lambda execution
2. **'emr'**: Always use EMR execution
3. **'auto'**: Intelligently select based on file size

### Validation Phase (Generate Request)
- If platform is 'auto', agent calls `select_execution_platform` first
- Agent calls the appropriate execution tool based on selected platform
- If validation fails, agent retries with error feedback (up to 3 attempts)
- No automatic fallback between platforms

### Execution Phase (Execute Request)
- If platform is 'auto', agent calls `select_execution_platform` first
- Agent calls the appropriate execution tool once
- No retries or regeneration
- Returns results directly

## No Breaking Changes

- All existing features preserved
- No simulations added
- Backend integration unchanged (still passes `execution_platform` parameter)
- Response format unchanged
- Error handling unchanged
- Supports 'lambda', 'emr', and 'auto' values for execution_platform

## Testing

To test the changes:

1. **Deploy the updated agent:**
   ```bash
   cd backend/spark-supervisor-agent
   conda activate bedrock-sdk
   python agent_deployment.py
   ```

2. **Test Lambda execution:**
   ```python
   payload = {
       "prompt": "Analyze data",
       "execution_platform": "lambda",
       "s3_output_path": "s3://bucket/output/",
       "session_id": "test-123"
   }
   ```

3. **Test EMR execution:**
   ```python
   payload = {
       "prompt": "Analyze data",
       "execution_platform": "emr",
       "s3_output_path": "s3://bucket/output/",
       "session_id": "test-123"
   }
   ```

4. **Test Auto selection (small file):**
   ```python
   payload = {
       "prompt": "Analyze data",
       "execution_platform": "auto",
       "s3_input_path": "s3://bucket/small-file.csv",  # < 500MB
       "s3_output_path": "s3://bucket/output/",
       "session_id": "test-123"
   }
   # Expected: Selects Lambda
   ```

5. **Test Auto selection (large file):**
   ```python
   payload = {
       "prompt": "Analyze data",
       "execution_platform": "auto",
       "file_size_mb": 1000,  # > 500MB
       "s3_output_path": "s3://bucket/output/",
       "session_id": "test-123"
   }
   # Expected: Selects EMR
   ```

## Files Modified

- `backend/spark-supervisor-agent/spark_supervisor_agent.py`
  - Removed: `execute_spark_code` tool
  - Added: `select_execution_platform` tool
  - Added: `execute_spark_code_lambda` tool
  - Added: `execute_spark_code_emr` tool
  - Updated: System prompt (added auto selection logic)
  - Updated: Agent tools list
  - Updated: Context building in invoke function
