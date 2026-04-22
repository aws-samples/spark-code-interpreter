"""MCP Tool: get_postgres_table_schema
Fetch schema for a PostgreSQL table by querying information_schema via JDBC.
"""

import json
import boto3


def lambda_handler(event, context):
    try:
        import psycopg2
    except ImportError:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': 'psycopg2 not available in this Lambda environment',
            }),
        }

    jdbc_url = event['jdbc_url']
    secret_arn = event['secret_arn']
    database = event['database']
    schema = event['schema']
    table = event['table']
    region = event.get('region', 'us-east-1')
    s3_bucket = event.get('s3_bucket', '')
    session_id = event.get('session_id', '')

    from progress import update_progress
    update_progress(s3_bucket, session_id, "get_postgres_table_schema", "running", f"Fetching schema for {schema}.{table}...", region)

    try:
        # Get credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name=region)
        secret = secrets_client.get_secret_value(SecretId=secret_arn)
        creds = json.loads(secret['SecretString'])

        # Parse JDBC URL: jdbc:postgresql://host:port/database
        jdbc_parts = jdbc_url.replace('jdbc:postgresql://', '').split('/')
        host_port = jdbc_parts[0].split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=creds['username'],
            password=creds['password'],
        )

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )

        columns = [
            {'name': row[0], 'type': row[1], 'nullable': row[2] == 'YES'}
            for row in cursor.fetchall()
        ]

        cursor.close()
        conn.close()

        result = {
            'status': 'success',
            'database': database,
            'schema': schema,
            'table': table,
            'columns': columns,
            'jdbc_url': jdbc_url,
        }

        update_progress(s3_bucket, session_id, "get_postgres_table_schema", "complete", f"Schema fetched: {len(columns)} columns", region)
        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'database': database,
                'schema': schema,
                'table': table,
            }),
        }
