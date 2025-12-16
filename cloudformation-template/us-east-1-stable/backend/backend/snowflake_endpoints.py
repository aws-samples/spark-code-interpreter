"""
Snowflake Integration Endpoints
Simplified implementation - connection string + manual table entry
"""

import json
import boto3
from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException

# Snowflake connection request model
class SnowflakeConnectionRequest(BaseModel):
    name: str
    account: str
    warehouse: str
    database: str
    schema: str = "PUBLIC"
    username: str
    password: str

# Snowflake table entry model (manual entry)
class SnowflakeTableEntry(BaseModel):
    full_table_name: str  # Format: DATABASE.SCHEMA.TABLE
    alias: Optional[str] = None

class SnowflakeTablesRequest(BaseModel):
    tables: list[SnowflakeTableEntry]
    session_id: str

def get_snowflake_secret(secret_name: str, region: str = "us-east-1"):
    """Retrieve Snowflake credentials from Secrets Manager"""
    try:
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Snowflake credentials: {str(e)}")

def test_snowflake_connection(account: str, warehouse: str, database: str, schema: str, username: str, password: str):
    """
    Test Snowflake connection
    Note: This is a simplified version. In production, you'd use snowflake-connector-python
    For now, we'll just validate the parameters
    """
    # Validate required fields
    if not all([account, warehouse, database, username, password]):
        return {
            "success": False,
            "message": "Missing required connection parameters"
        }
    
    # Basic validation
    if not account.endswith('.snowflakecomputing.com') and '.' not in account:
        # Add domain if not present
        account = f"{account}.snowflakecomputing.com"
    
    # In a real implementation, you would:
    # import snowflake.connector
    # conn = snowflake.connector.connect(
    #     account=account,
    #     user=username,
    #     password=password,
    #     warehouse=warehouse,
    #     database=database,
    #     schema=schema
    # )
    # conn.cursor().execute("SELECT CURRENT_VERSION()")
    
    return {
        "success": True,
        "message": f"Connection parameters validated for {account}",
        "account": account,
        "warehouse": warehouse,
        "database": database,
        "schema": schema
    }

def create_snowflake_connection_secret(connection_name: str, connection_data: dict, region: str = "us-east-1"):
    """Create or update Snowflake connection in Secrets Manager"""
    try:
        client = boto3.client('secretsmanager', region_name=region)
        
        secret_name = f"spark/snowflake/{connection_name}"
        secret_value = json.dumps({
            "account": connection_data["account"],
            "warehouse": connection_data["warehouse"],
            "database": connection_data["database"],
            "schema": connection_data.get("schema", "PUBLIC"),
            "username": connection_data["username"],
            "password": connection_data["password"]
        })
        
        try:
            # Try to create new secret
            response = client.create_secret(
                Name=secret_name,
                Description=f"Snowflake connection: {connection_name}",
                SecretString=secret_value
            )
            return {"success": True, "secret_arn": response['ARN'], "action": "created"}
        except client.exceptions.ResourceExistsException:
            # Secret exists, update it
            response = client.update_secret(
                SecretId=secret_name,
                SecretString=secret_value
            )
            return {"success": True, "secret_arn": response['ARN'], "action": "updated"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save Snowflake connection: {str(e)}")

def generate_snowflake_spark_code(prompt: str, tables: list, connection: dict):
    """
    Generate Spark code for Snowflake queries
    Simplified version - returns template code
    """
    
    # Build table list for prompt
    table_list = ", ".join([t.get("full_table_name", t.get("table", "")) for t in tables])
    
    code_template = f'''from pyspark.sql import SparkSession
import json

# Initialize Spark with Snowflake connector
spark = SparkSession.builder \\
    .appName("SnowflakeQuery") \\
    .config("spark.jars", "{connection.get('jdbc_driver_path', 's3://bucket/jars/snowflake-jdbc-3.14.4.jar')}") \\
    .getOrCreate()

# Snowflake connection options
sf_options = {{
    "sfURL": "{connection['account']}",
    "sfUser": "{connection['username']}",
    "sfPassword": "{connection['password']}",
    "sfDatabase": "{connection['database']}",
    "sfSchema": "{connection['schema']}",
    "sfWarehouse": "{connection['warehouse']}"
}}

# Read tables
# Available tables: {table_list}

# Example: Read first table
table_name = "{tables[0].get('full_table_name', 'DATABASE.SCHEMA.TABLE') if tables else 'YOUR_TABLE'}"

df = spark.read \\
    .format("net.snowflake.spark.snowflake") \\
    .options(**sf_options) \\
    .option("dbtable", table_name) \\
    .load()

# Your analysis here based on prompt: {prompt}
# Example operations:
# df.show(10)
# df.printSchema()
# result = df.groupBy("column").count()

# Write results to S3
output_path = "s3://your-bucket/output/snowflake_results"
# df.write.mode("overwrite").parquet(output_path)

# Return results as JSON
result_dict = {{
    "status": "success",
    "row_count": df.count(),
    "columns": df.columns,
    "sample_data": df.limit(10).toPandas().to_dict('records')
}}

# Write output for Lambda/EMR to return
with open('/tmp/output.json', 'w') as f:
    json.dump(result_dict, f)

print(json.dumps(result_dict))
'''
    
    return code_template
