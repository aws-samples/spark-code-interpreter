"""MCP Tool: generate_spark_code
Generate PySpark code from a natural language prompt using the Code Generation Agent.
"""

import json
import boto3


# The full Spark code generation system prompt (extracted from spark_supervisor_agent.py)
SPARK_SYSTEM_PROMPT = """You are a Spark code generation specialist.

Generate PySpark code for data analysis. Keep the code simple and direct.

CRITICAL - DO NOT SYNTHESIZE DATA:
- NEVER create sample data, synthetic data, or fake data in the code
- ALWAYS read from the actual data sources provided in the context
- Only generate sample data if the user explicitly requests it AND no data sources are provided

CRITICAL - SIMPLE, DIRECT CODE:
- Do NOT write column-matching loops or detection logic
- Do NOT iterate over columns to find matches
- Read the CSV with inferSchema=true, then use the actual column names directly
- If the user says "total sales", use the column named "total_sales" (or the closest match)
- If unsure which column, use df.printSchema() output to pick the right one, but hardcode the column name in the query

COLUMN SELECTION RULES (in priority order):
1. EXACT MATCH: If a column name exactly matches what the user asked for, use it
2. CONTAINS FULL TERM: "total_sales" matches "total sales" better than "unit_price" matches "sales"
3. PREFER AGGREGATED COLUMNS: For sum/total queries, prefer columns with "total" in the name over raw unit values
4. NEVER loop through columns at runtime to find matches — decide the column at code-generation time

EXAMPLE - CORRECT (simple, direct):
```python
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum

spark = SparkSession.builder.appName("Query").getOrCreate()
df = spark.read.option("header", "true").option("inferSchema", "true").csv("s3://bucket/data.csv")

result = df.filter(col("category") == "Electronics").agg(_sum("total_sales").alias("total_sales"))
result.show()

data = [row.asDict() for row in result.collect()]
with open('/tmp/output.json', 'w') as f:
    json.dump({"status": "success", "row_count": len(data), "data": data}, f)
spark.stop()
```

EXAMPLE - WRONG (do NOT generate code like this):
```python
# DO NOT DO THIS - no runtime column detection loops
for col_name in columns:
    if 'sales' in col_name.lower():
        sales_col = col_name
        break
```

DATA SOURCES:
- S3 files: Use spark.read.option("header", "true").option("inferSchema", "true").csv(s3_path)
- Glue tables: Use spark.table("database.table") with Glue catalog configuration
- PostgreSQL tables: Use JDBC with credentials based on auth_method from context

CRITICAL - SPARK COLUMN OPERATIONS:
- NEVER use Python lists directly in Spark operations
- For filtering: Use col("column").isin([val1, val2, val3])
- Always import: from pyspark.sql.functions import col, lit, sum as _sum, count, avg, etc.
- Use _sum instead of sum to avoid shadowing Python's built-in sum

CRITICAL - GLUE CATALOG CONFIGURATION:
When the prompt mentions Glue tables, include:
spark = SparkSession.builder \\
    .appName("GlueQuery") \\
    .config("spark.sql.warehouse.dir", "ACTUAL_S3_BUCKET_FROM_CONTEXT") \\
    .config("spark.hadoop.hive.metastore.warehouse.dir", "ACTUAL_S3_BUCKET_FROM_CONTEXT") \\
    .config("hive.metastore.client.factory.class",
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \\
    .enableHiveSupport() \\
    .getOrCreate()

POSTGRESQL DATA SOURCES:
When PostgreSQL tables are in context, use JDBC connection with exact values from context.
Use auth_method from context (secrets_manager, iam, or user_password).

CRITICAL - OUTPUT FILE REQUIREMENTS (MANDATORY):
1. Import json at the top: import json
2. Write output before spark.stop()
3. Use appropriate strategy based on result size:
   - Simple calculations: Write result directly to /tmp/output.json
   - Small results (<1000 rows): Collect and write to /tmp/output.json
   - Large results (>1000 rows): Write to S3, return sample in /tmp/output.json

Return only executable Python code with intelligent column matching and MANDATORY output file writing."""


def _build_data_context(event):
    """Build the data context string from event parameters."""
    parts = []

    s3_input_path = event.get('s3_input_path')
    if s3_input_path:
        parts.append(f"\nS3 CSV file: {s3_input_path}")

    selected_tables = event.get('selected_tables')
    if selected_tables:
        if selected_tables and isinstance(selected_tables[0], dict):
            table_names = [f"{t['database']}.{t['table']}" for t in selected_tables]
            parts.append(f"\nGlue tables: {', '.join(table_names)}")
            if selected_tables[0].get('location'):
                parts.append(f"\nS3 bucket for warehouse: {selected_tables[0]['location']}")
        else:
            parts.append(f"\nGlue tables: {', '.join(selected_tables)}")
            s3_output_path = event.get('s3_output_path', '')
            if s3_output_path and s3_output_path.startswith('s3://'):
                bucket = s3_output_path.split('/')[2]
                parts.append(f"\nS3 bucket for warehouse: s3://{bucket}/warehouse/")

    selected_postgres_tables = event.get('selected_postgres_tables')
    if selected_postgres_tables:
        pg_context = "\n\nPostgreSQL tables:\n"
        for pg_table in selected_postgres_tables:
            pg_context += f"- Connection: {pg_table['connection_name']}\n"
            pg_context += f"  {pg_table['database']}.{pg_table['schema']}.{pg_table['table']}\n"
            pg_context += f"  JDBC URL: {pg_table['jdbc_url']}\n"
            pg_context += f"  Auth Method: {pg_table.get('auth_method', 'secrets_manager')}\n"
            pg_context += f"  Secret ARN: {pg_table['secret_arn']}\n"
            if pg_table.get('auth_method') == 'iam':
                pg_context += f"  Host: {pg_table.get('host', '')}\n"
                pg_context += f"  Port: {pg_table.get('port', 5432)}\n"
            if 'columns' in pg_table and pg_table['columns']:
                cols = ', '.join([f"{c['name']} ({c['type']})" for c in pg_table['columns'][:5]])
                pg_context += f"  Columns: {cols}\n"
        parts.append(pg_context)

        jdbc_driver = event.get('jdbc_driver_path')
        if jdbc_driver:
            parts.append(f"\nJDBC Driver: {jdbc_driver}\n")

    s3_output_path = event.get('s3_output_path')
    if s3_output_path:
        parts.append(f"\nWrite results to: {s3_output_path}")

    return ''.join(parts)


def lambda_handler(event, context):
    try:
        prompt = event['prompt']
        session_id = event['session_id']
        model_id = event['model_id']
        code_gen_agent_arn = event['code_gen_agent_arn']
        region = event.get('region', 'us-east-1')
        s3_bucket = event.get('s3_bucket', '')

        from progress import update_progress
        update_progress(s3_bucket, session_id, "generate_spark_code", "running", "Generating PySpark code...", region)

        # Build data context from parameters
        data_context = _build_data_context(event)
        full_prompt = f"{prompt}{data_context}"

        payload = {
            'prompt': full_prompt,
            'system_prompt': SPARK_SYSTEM_PROMPT,
            'session_id': session_id,
            'model_id': model_id,
        }

        agentcore_client = boto3.client(
            'bedrock-agentcore',
            region_name=region,
            config=boto3.session.Config(read_timeout=300, connect_timeout=60),
        )

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=code_gen_agent_arn,
            runtimeSessionId=session_id,
            qualifier='DEFAULT',
            payload=json.dumps(payload),
        )

        if 'response' in response:
            code = response['response'].read().decode('utf-8')
            if code.startswith('```python'):
                code = code[10:-3].strip()
            elif code.startswith('```'):
                code = code[3:-3].strip()
            lines = len(code.strip().split('\n'))
            update_progress(s3_bucket, session_id, "generate_spark_code", "complete", f"Generated {lines} lines of PySpark code", region)
            return {'statusCode': 200, 'body': json.dumps({'status': 'success', 'code': code})}
        else:
            update_progress(s3_bucket, session_id, "generate_spark_code", "error", "No response from agent", region)
            return {'statusCode': 500, 'body': json.dumps({'status': 'error', 'error': 'No response from code generation agent'})}

    except Exception as e:
        from progress import update_progress
        update_progress(event.get('s3_bucket', ''), event.get('session_id', ''), "generate_spark_code", "error", str(e), event.get('region', 'us-east-1'))
        return {'statusCode': 500, 'body': json.dumps({'status': 'error', 'error': str(e)})}
