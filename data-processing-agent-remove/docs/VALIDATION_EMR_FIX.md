# Validation Failure and EMR Preference Fix

## Issues Fixed

### 1. Validation Failure Not Being Caught
**Problem**: The Spark supervisor agent was not properly checking validation status before executing code, leading to failed validations being executed anyway.

**Solution**: Updated system prompt to explicitly check `validation.status`:
- If `validation.status == 'validation_failed'`, retry code generation (up to 5 attempts)
- If `validation.status == 'success'`, proceed to execution
- Validation failures now trigger regeneration instead of execution

### 2. EMR Preference for Glue Tables
**Problem**: EMR preference was being set in the Spark supervisor agent, but should be set in the backend when tables are selected from the frontend.

**Solution**: 
- **Backend (`backend/main.py`)**: Added logic to prefer EMR when `selected_tables` are provided:
  ```python
  # Prefer EMR for Glue table queries
  if selected_tables_list and request.execution_platform == 'lambda':
      execution_platform = 'emr'
  else:
      execution_platform = request.execution_engine if request.execution_engine != 'auto' else request.execution_platform
  ```
- **Spark Supervisor Agent**: Removed EMR preference logic - now just uses the platform specified by backend

### 3. Execute-Only Mode Clarification
**Problem**: Execute-only calls should execute once without retries, but the workflow wasn't clear.

**Solution**: Updated execute-only context to be explicit:
- Skip steps 1-4 (schema fetch, code generation, extraction, validation)
- Execute code ONCE on specified platform
- Do NOT retry or regenerate code in execute-only mode

## Workflow Clarification

### Generation + Validation + Execution Mode
1. Fetch Glue table schemas (if tables selected)
2. Generate Spark code
3. Extract Python code
4. **Validate code** (static checks)
   - If validation fails → Retry generation (up to 5 attempts)
   - If validation succeeds → Proceed to execution
5. **Execute code ONCE** on specified platform
6. If execution fails → Retry generation with error feedback (up to 5 attempts total)
7. Extract logs and fetch results
8. Return response

### Execute-Only Mode
1. Skip all generation/validation steps
2. **Execute provided code ONCE** on specified platform
3. Extract logs and fetch results
4. Return response
5. **NO RETRIES** in execute-only mode

## Key Points

- **Validation** = Static code checks (SparkSession exists, correct data source usage, etc.)
- **Execution** = Actually running the code on Lambda/EMR
- **Retries** = Only for generation/validation failures, not execution failures in execute-only mode
- **EMR Preference** = Set in backend when tables are selected, not in agent
- **System Prompt** = Parameterized and working correctly for Spark-specific code generation

## Code Generation Agent

The code generation agent (`ray_code_interpreter-oTKmLH9IB9`) is shared between Ray and Spark:
- Accepts `system_prompt` parameter to customize behavior
- Spark supervisor passes Spark-specific system prompt with Glue catalog configuration
- Ray supervisor passes Ray-specific system prompt with distributed computing patterns
- This parameterization is working as expected

## Testing

To verify the fixes:
1. Select a Glue table from frontend
2. Backend should automatically set `execution_platform='emr'`
3. Generate code with validation errors (e.g., missing SparkSession)
4. Agent should retry generation, not execute invalid code
5. Execute-only calls should execute once without retries
