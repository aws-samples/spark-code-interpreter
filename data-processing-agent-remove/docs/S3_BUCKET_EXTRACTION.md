# S3 Bucket Extraction for Glue Tables - Current State and Recommendations

## Deployment Status

✅ **Agent Successfully Deployed**
- ARN: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR`
- Status: Accessible and responding
- Note: CLI module warning is harmless, deployment completed successfully

## Current S3 Bucket Extraction

### What Exists

1. **`fetch_glue_table_schema` Tool** ✅
   - Fetches table metadata from Glue Data Catalog
   - Returns: `location` field with full S3 path (e.g., `s3://bucket/path/to/table/`)
   - Also returns: columns, partition keys, table type, etc.

2. **Current Extraction Logic** ⚠️
   ```python
   # In call_code_generation_agent
   if s3_output_path:
       bucket = s3_output_path.split('/')[2]
       data_context += f"\nS3 bucket for warehouse: s3://{bucket}/warehouse/"
   ```
   - Extracts bucket from OUTPUT path, not table location
   - Fallback: Uses default bucket if no output path

### What's Missing

1. **Table Location Not Passed to Code Generation**
   - Supervisor calls `fetch_glue_table_schema` and gets table location
   - But this location is NOT passed to `call_code_generation_agent`
   - Code generation only receives table names, not S3 locations

2. **No Database Description Tool**
   - No tool to get database-level S3 location
   - Some databases have a default location for all tables

## How It Currently Works

### Workflow
```
1. Supervisor: fetch_glue_table_schema("northwind", "nasdaq")
   Returns: {
     "location": "s3://my-data-bucket/northwind/nasdaq/",
     "columns": [...],
     ...
   }

2. Supervisor: call_code_generation_agent(
     prompt="Query nasdaq table",
     selected_tables=["northwind.nasdaq"],
     s3_output_path="s3://spark-data-260005718447-us-east-1/output/"
   )
   
3. Code Generation receives:
   - Table names: "northwind.nasdaq"
   - S3 bucket: "spark-data-260005718447-us-east-1" (from OUTPUT path)
   - ❌ Does NOT receive table location: "s3://my-data-bucket/..."

4. Generated code uses:
   .config("spark.sql.warehouse.dir", "s3://spark-data-260005718447-us-east-1/warehouse/")
   # Uses OUTPUT bucket, not table's actual bucket
```

## Recommendations

### Option 1: Pass Table Locations to Code Generation (Recommended)

**Modify supervisor system prompt:**
```
When calling call_code_generation_agent for Glue tables:
1. First call fetch_glue_table_schema for each table
2. Extract S3 bucket from table location
3. Pass table locations in the prompt context
4. Example: "Table northwind.nasdaq at s3://my-data-bucket/northwind/nasdaq/"
```

**Benefits:**
- Uses actual table bucket for warehouse configuration
- More accurate and reliable
- Follows data locality principle

### Option 2: Add Database Description Tool

**Create new tool:**
```python
@tool
def fetch_glue_database_info(database_name: str) -> dict:
    """Get database metadata including default location"""
    glue_client = boto3.client('glue', region_name='us-east-1')
    response = glue_client.get_database(Name=database_name)
    return {
        'name': database_name,
        'location': response['Database'].get('LocationUri', ''),
        'description': response['Database'].get('Description', '')
    }
```

**Benefits:**
- Gets database-level default location
- Useful when tables don't have individual locations
- Can be used as fallback

### Option 3: Keep Current Implementation (Simplest)

**Current behavior:**
- Uses output bucket for warehouse configuration
- Works if output bucket has proper permissions
- Simpler, fewer moving parts

**Limitations:**
- May not match table's actual bucket
- Could cause permission issues if buckets differ
- Less optimal for data locality

## Current Status Assessment

### What Works ✅
- Agent deployed successfully
- `fetch_glue_table_schema` returns table location
- S3 bucket extracted from output path as fallback
- Glue catalog configuration included in generated code

### What Could Be Improved 🔄
- Table location from `fetch_glue_table_schema` not utilized
- Warehouse bucket may not match table bucket
- No database-level location tool

### What's Acceptable for Now ✓
- Using output bucket for warehouse is valid
- Works if all data in same bucket or cross-bucket access allowed
- Can be enhanced later without breaking changes

## Testing Current Implementation

```python
# Test with northwind.nasdaq
payload = {
    "prompt": "Find top 10 by closing price",
    "selected_tables": [{"database": "northwind", "table": "nasdaq"}],
    "execution_engine": "lambda"
}

# Expected behavior:
# 1. Fetches nasdaq table schema (gets location)
# 2. Generates code with warehouse config using OUTPUT bucket
# 3. Code should work if:
#    - Output bucket has Glue permissions
#    - Cross-bucket access allowed
#    - Or table is in same bucket as output
```

## Recommendation for Next Steps

**Immediate (Current State):**
- ✅ Keep current implementation
- ✅ Test with actual Glue tables
- ✅ Verify warehouse configuration works

**Short-term Enhancement:**
- Update supervisor prompt to pass table locations to code generation
- Extract bucket from table location instead of output path
- More accurate warehouse configuration

**Long-term Enhancement:**
- Add database description tool
- Support multi-bucket scenarios
- Optimize for data locality

## Conclusion

**Deployment:** ✅ Successful

**S3 Bucket Extraction:** ⚠️ Works but suboptimal
- Currently uses output bucket
- Table location available but not utilized
- Acceptable for single-bucket scenarios
- Should be enhanced for production use

**Next Action:** Test with real Glue tables to verify current implementation works
