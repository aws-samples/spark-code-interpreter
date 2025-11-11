# Glue Table Execution Issues - Analysis and Recommendations

## Current Issues

### 1. Lambda: "Execution return larger than expected payload"
**Symptom**: When selecting Glue tables and executing on Lambda, getting payload size error

**Root Cause**: Lambda is trying to use `enableHiveSupport()` which requires Derby metastore database
- Lambda tries to create `/var/task/metastore_db` directory
- Lambda `/var/task` is read-only, causing error: `ERROR XBM0H: Directory /var/task/metastore_db cannot be created`
- This causes Lambda execution to fail or return incomplete results

**Evidence from Logs**:
```
ERROR XJ041: Failed to create database 'metastore_db'
ERROR XBM0H: Directory /var/task/metastore_db cannot be created
```

### 2. EMR: "Execution failed status with empty output"
**Symptom**: EMR execution shows failed status with no output when using Glue tables

**Likely Cause**: Similar Hive metastore configuration issue or missing Glue permissions

## Key Differences from Reference Implementation

### Reference Implementation (`spark-code-interpreter-strands_dev`)

1. **Dedicated Glue Tools**:
   - `glue_catalog_tool.py` - Fetches detailed table schemas
   - `glue_code_generation_tool.py` - Specialized code generation for Glue tables
   - `get_table_schema()` - Returns full schema with columns, partitions, location

2. **Code Generation Approach**:
   - Fetches complete table schema BEFORE code generation
   - Passes detailed schema context to LLM
   - Post-processes generated code to ensure proper Glue table usage
   - Replaces `spark.read` with `spark.table()` calls
   - Ensures `enableHiveSupport()` is added

3. **Validation Strategy**:
   - Uses static validation only (no local execution)
   - Avoids "broken pipe" errors by skipping local validation
   - Relies on EMR/Lambda for actual execution

### Current Implementation (AgentCore)

1. **Glue Tool**:
   - `fetch_glue_table_schema()` - Basic schema fetching
   - Called by supervisor agent during workflow
   - Schema passed to code generation agent

2. **Code Generation**:
   - Uses shared code generation agent
   - System prompt mentions Glue tables but may not have detailed schema context
   - No post-processing to ensure proper Glue table usage

3. **Validation**:
   - Uses same validation flow as CSV files
   - May attempt local validation which fails for Glue tables

## Recommendations

### Immediate Fixes

#### 1. Fix Lambda Hive Metastore Issue

**Option A: Use Glue Catalog as Metastore (Recommended)**
```python
spark = SparkSession.builder \
    .appName("GlueQuery") \
    .config("spark.sql.catalogImplementation", "hive") \
    .config("hive.metastore.client.factory.class", 
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \
    .enableHiveSupport() \
    .getOrCreate()
```

**Option B: Use In-Memory Metastore**
```python
spark = SparkSession.builder \
    .appName("GlueQuery") \
    .config("spark.sql.catalogImplementation", "in-memory") \
    .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
    .getOrCreate()

# Then use spark.read.format("parquet").load(s3_path) instead of spark.table()
```

**Option C: Direct S3 Read (No Hive)**
```python
# Don't use enableHiveSupport()
spark = SparkSession.builder.appName("GlueQuery").getOrCreate()

# Read directly from S3 location
df = spark.read.format("parquet").load("s3://bucket/path/")
```

#### 2. Update Code Generation System Prompt

Add Glue-specific instructions:
```
For Glue tables:
- DO NOT use enableHiveSupport() on Lambda
- Use spark.read.format("parquet").load(s3_location) instead of spark.table()
- Get S3 location from table schema
- For EMR: Can use enableHiveSupport() with Glue catalog configuration
```

#### 3. Add Platform-Specific Code Generation

```python
if execution_platform == "lambda":
    # Lambda: Direct S3 read, no Hive
    system_prompt += "\nFor Lambda: Use spark.read.format().load(s3_path), NOT spark.table()"
elif execution_platform == "emr":
    # EMR: Can use Glue catalog
    system_prompt += "\nFor EMR: Use Glue catalog with proper configuration"
```

### Long-term Improvements

1. **Separate Glue Code Generation Tool**
   - Create dedicated tool like reference implementation
   - Fetch full schema before generation
   - Post-process code to ensure correct patterns

2. **Add Glue Permissions**
   - Lambda execution role needs: `glue:GetTable`, `glue:GetDatabase`, `glue:GetPartitions`
   - Spark supervisor agent role needs same permissions

3. **Skip Local Validation for Glue**
   - Detect Glue table usage in code
   - Skip validation, go straight to execution
   - Validation happens on actual platform (Lambda/EMR)

4. **Add Result Size Limits**
   - Limit rows returned from Glue queries
   - Add `.limit(1000)` to generated queries
   - Prevent payload size issues

## Testing Strategy

### Test 1: Lambda with Direct S3 Read
```python
# Generate code that reads from S3 directly
prompt = "Read data from s3://bucket/path/ and show first 10 rows"
# Should work without Hive metastore
```

### Test 2: EMR with Glue Catalog
```python
# Generate code with proper Glue catalog config
prompt = "Query database.table and show first 10 rows"
execution_engine = "emr"
# Should work with Glue catalog
```

### Test 3: Schema Fetching
```python
# Verify schema is fetched and passed to code gen
selected_tables = ["database.table"]
# Check that fetch_glue_table_schema is called
# Verify schema in code generation context
```

## Implementation Priority

1. **HIGH**: Fix Lambda Hive metastore issue (Option C - Direct S3 read)
2. **HIGH**: Update system prompt to avoid enableHiveSupport() on Lambda
3. **MEDIUM**: Add platform-specific code generation logic
4. **MEDIUM**: Add Glue permissions to execution roles
5. **LOW**: Create dedicated Glue code generation tool
6. **LOW**: Implement result size limits

## Files to Modify

1. `backend/spark-supervisor-agent/spark_supervisor_agent.py`
   - Update `call_code_generation_agent` system prompt
   - Add platform-specific instructions

2. `backend/spark-supervisor-agent/spark_supervisor_agent.py`
   - Enhance `fetch_glue_table_schema` to return S3 location
   - Pass location to code generation

3. Lambda execution role (IAM)
   - Add Glue permissions

4. Spark supervisor agent role (IAM)
   - Add Glue permissions

## Expected Behavior After Fixes

- **Lambda**: Reads Glue table data directly from S3, no Hive metastore needed
- **EMR**: Uses Glue catalog as Hive metastore, proper table queries
- **Both**: Return formatted results in Outputs section
- **Both**: Handle large result sets gracefully
