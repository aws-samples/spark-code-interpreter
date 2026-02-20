from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import json
import pymysql
import psycopg2
from typing import Dict, Any, Optional, List

rds = boto3.client('rds')
secrets_client = boto3.client('secretsmanager')

def get_db_credentials(secret_name: str) -> Dict[str, str]:
    """Get database credentials from Secrets Manager."""
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        raise Exception(f"Failed to get credentials: {str(e)}")

@tool
def execute_query(secret_name: str, db_name: str, query: str, db_type: str = 'mysql') -> Dict[str, Any]:
    """Execute SQL query on RDS database.
    
    Args:
        secret_name: Secrets Manager secret name for DB credentials
        db_name: Database name
        query: SQL query to execute
        db_type: Database type (mysql or postgresql)
    
    Returns:
        Dictionary containing query results
    """
    try:
        creds = get_db_credentials(secret_name)
        
        if db_type.lower() == 'mysql':
            conn = pymysql.connect(host=creds['host'], user=creds['username'], password=creds['password'], database=db_name)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
        else:
            conn = psycopg2.connect(host=creds['host'], user=creds['username'], password=creds['password'], database=db_name)
            cursor = conn.cursor()
        
        cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            return {'results': results, 'count': len(results)}
        else:
            conn.commit()
            return {'message': 'Query executed successfully', 'affected_rows': cursor.rowcount}
        
    except Exception as e:
        return {'error': str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

@tool
def list_tables(secret_name: str, db_name: str, db_type: str = 'mysql') -> Dict[str, Any]:
    """List all tables in the database.
    
    Args:
        secret_name: Secrets Manager secret name for DB credentials
        db_name: Database name
        db_type: Database type (mysql or postgresql)
    
    Returns:
        Dictionary containing table names
    """
    try:
        if db_type.lower() == 'mysql':
            query = "SHOW TABLES"
        else:
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        
        result = execute_query(secret_name, db_name, query, db_type)
        return result
    except Exception as e:
        return {'error': str(e)}

@tool
def describe_table(secret_name: str, db_name: str, table_name: str, db_type: str = 'mysql') -> Dict[str, Any]:
    """Describe table structure.
    
    Args:
        secret_name: Secrets Manager secret name for DB credentials
        db_name: Database name
        table_name: Name of the table
        db_type: Database type (mysql or postgresql)
    
    Returns:
        Dictionary containing table structure
    """
    try:
        if db_type.lower() == 'mysql':
            query = f"DESCRIBE {table_name}"
        else:
            query = f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}'"
        
        result = execute_query(secret_name, db_name, query, db_type)
        return result
    except Exception as e:
        return {'error': str(e)}

@tool
def insert_record(secret_name: str, db_name: str, table_name: str, data: Dict[str, Any], db_type: str = 'mysql') -> Dict[str, Any]:
    """Insert a record into table.
    
    Args:
        secret_name: Secrets Manager secret name for DB credentials
        db_name: Database name
        table_name: Name of the table
        data: Dictionary of column-value pairs
        db_type: Database type (mysql or postgresql)
    
    Returns:
        Dictionary containing success message
    """
    try:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        result = execute_query(secret_name, db_name, query, db_type)
        return result
    except Exception as e:
        return {'error': str(e)}

@tool
def update_record(secret_name: str, db_name: str, table_name: str, data: Dict[str, Any], where_clause: str, db_type: str = 'mysql') -> Dict[str, Any]:
    """Update records in table.
    
    Args:
        secret_name: Secrets Manager secret name for DB credentials
        db_name: Database name
        table_name: Name of the table
        data: Dictionary of column-value pairs to update
        where_clause: WHERE clause for the update
        db_type: Database type (mysql or postgresql)
    
    Returns:
        Dictionary containing success message
    """
    try:
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        
        result = execute_query(secret_name, db_name, query, db_type)
        return result
    except Exception as e:
        return {'error': str(e)}

@tool
def delete_record(secret_name: str, db_name: str, table_name: str, where_clause: str, db_type: str = 'mysql') -> Dict[str, Any]:
    """Delete records from table.
    
    Args:
        secret_name: Secrets Manager secret name for DB credentials
        db_name: Database name
        table_name: Name of the table
        where_clause: WHERE clause for the deletion
        db_type: Database type (mysql or postgresql)
    
    Returns:
        Dictionary containing success message
    """
    try:
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        result = execute_query(secret_name, db_name, query, db_type)
        return result
    except Exception as e:
        return {'error': str(e)}

@tool
def generate_simple_sql(operation: str, table_name: str, columns: Optional[List[str]] = None, conditions: Optional[str] = None) -> Dict[str, Any]:
    """Generate simple SQL queries from text description.
    
    Args:
        operation: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        table_name: Name of the table
        columns: List of columns (for SELECT, INSERT)
        conditions: WHERE conditions
    
    Returns:
        Dictionary containing generated SQL
    """
    try:
        operation = operation.upper()
        
        if operation == 'SELECT':
            cols = ', '.join(columns) if columns else '*'
            query = f"SELECT {cols} FROM {table_name}"
            if conditions:
                query += f" WHERE {conditions}"
        
        elif operation == 'INSERT':
            if not columns:
                return {'error': 'Columns required for INSERT'}
            placeholders = ', '.join(['%s'] * len(columns))
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        elif operation == 'UPDATE':
            if not columns:
                return {'error': 'Columns required for UPDATE'}
            set_clause = ', '.join([f"{col} = %s" for col in columns])
            query = f"UPDATE {table_name} SET {set_clause}"
            if conditions:
                query += f" WHERE {conditions}"
        
        elif operation == 'DELETE':
            query = f"DELETE FROM {table_name}"
            if conditions:
                query += f" WHERE {conditions}"
        
        else:
            return {'error': f'Unsupported operation: {operation}'}
        
        return {'sql': query}
    except Exception as e:
        return {'error': str(e)}

@tool
def generate_complex_sql(description: str, table_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate complex SQL queries from natural language description.
    
    Args:
        description: Natural language description of the query
        table_info: Optional table schema information
    
    Returns:
        Dictionary containing generated SQL
    """
    try:
        return {
            'sql': f"-- Generated SQL for: {description}",
            'description': description,
            'note': 'Complex SQL generation requires additional model processing'
        }
    except Exception as e:
        return {'error': str(e)}

# Create the RDS agent
rds_agent = Agent(
    model=BedrockModel(model_id="anthropic.claude-3-sonnet-20240229-v1:0"),
    system_prompt="""You are an RDS assistant that helps users manage databases and execute SQL queries.
    Database credentials are automatically retrieved from AWS Secrets Manager.
    You can execute queries, list tables, describe table structures, insert/update/delete records, and generate SQL from text.
    The database name and table name are provided as parameters. Be helpful and provide clear responses about the operations performed.
    For SQL generation, help users create both simple and complex queries based on their requirements.""",
    tools=[execute_query, list_tables, describe_table, insert_record, update_record, delete_record, generate_simple_sql, generate_complex_sql]
)

def handler(event: Dict[str, Any], context) -> str:
    """Lambda handler for RDS operations using Strands agent."""
    try:
        # Get parameters from event
        secret_name = event.get('secret_name', '')
        db_name = event.get('db_name', '')
        table_name = event.get('table_name', '')
        body = event.get('body', '')
        
        if not secret_name or not db_name:
            return json.dumps({'error': 'secret_name and db_name are required'})
        
        # Create context-aware prompt
        prompt = f"Database: {db_name}, Table: {table_name}, Request: {body}"
        
        response = rds_agent(prompt)
        return str(response)
    
    except Exception as e:
        return json.dumps({'error': str(e)})