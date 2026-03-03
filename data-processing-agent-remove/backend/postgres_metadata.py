import psycopg2
import boto3
import json
from functools import lru_cache
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PostgresMetadataFetcher:
    """Fetch metadata from PostgreSQL databases"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.secrets_client = boto3.client('secretsmanager', region_name=region)
        self._connections = {}
    
    @lru_cache(maxsize=10)
    def _get_credentials(self, secret_arn: str) -> dict:
        """Get credentials from Secrets Manager with caching"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_arn)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to get credentials from {secret_arn}: {e}")
            raise
    
    def _get_connection(self, secret_arn: str):
        """Get or create database connection"""
        if secret_arn in self._connections:
            conn = self._connections[secret_arn]
            try:
                conn.isolation_level
                return conn
            except:
                del self._connections[secret_arn]
        
        creds = self._get_credentials(secret_arn)
        
        # Handle IAM authentication
        if creds.get('auth_method') == 'iam':
            # Generate IAM auth token
            rds_client = boto3.client('rds', region_name=self.region)
            token = rds_client.generate_db_auth_token(
                DBHostname=creds['host'],
                Port=creds['port'],
                DBUsername=creds['username'],
                Region=self.region
            )
            conn = psycopg2.connect(
                host=creds['host'],
                port=creds['port'],
                database=creds['database'],
                user=creds['username'],
                password=token,
                connect_timeout=10,
                sslmode='require'
            )
        else:
            # Standard username/password auth
            conn = psycopg2.connect(
                host=creds['host'],
                port=creds['port'],
                database=creds['database'],
                user=creds['username'],
                password=creds['password'],
                connect_timeout=10
            )
        
        self._connections[secret_arn] = conn
        return conn
    
    def list_databases(self, secret_arn: str) -> List[str]:
        """List all databases"""
        try:
            conn = self._get_connection(secret_arn)
            with conn.cursor() as cur:
                cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            raise
    
    def list_schemas(self, secret_arn: str, database: str) -> List[str]:
        """List schemas in a database"""
        try:
            creds = self._get_credentials(secret_arn)
            conn = psycopg2.connect(
                host=creds['host'],
                port=creds['port'],
                database=database,
                user=creds['username'],
                password=creds['password'],
                connect_timeout=10
            )
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT schema_name FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY schema_name
                """)
                schemas = [row[0] for row in cur.fetchall()]
            conn.close()
            return schemas
        except Exception as e:
            logger.error(f"Failed to list schemas: {e}")
            raise
    
    def list_tables(self, secret_arn: str, database: str, schema: str) -> List[Dict]:
        """List tables with column metadata"""
        try:
            creds = self._get_credentials(secret_arn)
            conn = psycopg2.connect(
                host=creds['host'],
                port=creds['port'],
                database=database,
                user=creds['username'],
                password=creds['password'],
                connect_timeout=10
            )
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        t.table_name,
                        json_agg(
                            json_build_object(
                                'name', c.column_name,
                                'type', c.data_type,
                                'nullable', c.is_nullable = 'YES'
                            ) ORDER BY c.ordinal_position
                        ) as columns
                    FROM information_schema.tables t
                    LEFT JOIN information_schema.columns c 
                        ON t.table_schema = c.table_schema 
                        AND t.table_name = c.table_name
                    WHERE t.table_schema = %s AND t.table_type = 'BASE TABLE'
                    GROUP BY t.table_name
                    ORDER BY t.table_name
                """, (schema,))
                tables = []
                for row in cur.fetchall():
                    tables.append({
                        'name': row[0],
                        'schema': schema,
                        'columns': row[1] if row[1] else []
                    })
            conn.close()
            return tables
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            raise
    
    def get_table_schema(self, secret_arn: str, database: str, schema: str, table: str) -> Dict:
        """Get detailed schema for a specific table"""
        try:
            creds = self._get_credentials(secret_arn)
            conn = psycopg2.connect(
                host=creds['host'],
                port=creds['port'],
                database=database,
                user=creds['username'],
                password=creds['password'],
                connect_timeout=10
            )
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable = 'YES' as nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, table))
                columns = [
                    {'name': row[0], 'type': row[1], 'nullable': row[2]}
                    for row in cur.fetchall()
                ]
            conn.close()
            
            jdbc_url = f"jdbc:postgresql://{creds['host']}:{creds['port']}/{database}"
            
            return {
                'database': database,
                'schema': schema,
                'table': table,
                'jdbc_url': jdbc_url,
                'columns': columns
            }
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            raise
    
    def close_all(self):
        """Close all cached connections"""
        for conn in self._connections.values():
            try:
                conn.close()
            except:
                pass
        self._connections.clear()

_fetcher_instance = None

def get_postgres_metadata_fetcher() -> PostgresMetadataFetcher:
    """Get singleton instance"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = PostgresMetadataFetcher()
    return _fetcher_instance
