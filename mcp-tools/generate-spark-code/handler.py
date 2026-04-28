"""MCP Tool: generate_spark_code
Generate PySpark code from a natural language prompt using the Code Generation Agent.
"""

import json
import boto3


# The full Spark code generation system prompt (extracted from spark_supervisor_agent.py)
SPARK_SYSTEM_PROMPT = """You are a Spark code generation specialist with intelligent column matching capabilities.

Generate PySpark code for data analysis with automatic column name resolution.

CRITICAL - DO NOT SYNTHESIZE DATA:
- NEVER create sample data, synthetic data, or fake data in the code
- NEVER use createDataFrame with hardcoded values
- ALWAYS read from the actual data sources provided in the context
- If data sources are provided (S3, Glue, PostgreSQL), you MUST read from them
- Only generate sample data if the user explicitly requests it AND no data sources are provided

INTELLIGENT COLUMN MATCHING:
- When user mentions column names that don't exactly match, find the closest matching column
- Use fuzzy matching, partial matching, and semantic understanding

DATA SOURCES:
- S3 files: Use spark.read.option("header", "true").csv(s3_path)
- Glue tables: Use spark.table("database.table") with Glue catalog configuration
- PostgreSQL tables: Use JDBC with credentials based on auth_method from context

CRITICAL - SPARK COLUMN OPERATIONS:
- NEVER use Python lists directly in Spark operations
- For filtering multiple values: Use col("column").isin([val1, val2, val3])
- For array literals: Use array([lit(val1), lit(val2), lit(val3)])
- Always import required functions: from pyspark.sql.functions import col, lit, array, when, etc.

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
            # Clean up code blocks
            if code.startswith('```python'):
                code = code[10:-3].strip()
            elif code.startswith('```'):
                code = code[3:-3].strip()
            return {'statusCode': 200, 'body': json.dumps({'status': 'success', 'code': code})}
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'status': 'error', 'error': 'No response from code generation agent'}),
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'status': 'error', 'error': str(e)}),
        }
