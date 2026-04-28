"""MCP Tool: get_glue_table_schema
Fetch detailed schema for an AWS Glue table including columns, types, and partitions.
"""

import json
import boto3


def lambda_handler(event, context):
    try:
        database_name = event['database_name']
        table_name = event['table_name']
        region = event.get('region', 'us-east-1')

        glue_client = boto3.client('glue', region_name=region)
        response = glue_client.get_table(DatabaseName=database_name, Name=table_name)
        table = response['Table']

        storage_desc = table.get('StorageDescriptor', {})
        columns = [
            {'name': col['Name'], 'type': col['Type'], 'comment': col.get('Comment', '')}
            for col in storage_desc.get('Columns', [])
        ]
        partition_keys = [
            {'name': pk['Name'], 'type': pk['Type']}
            for pk in table.get('PartitionKeys', [])
        ]

        result = {
            'status': 'success',
            'database': database_name,
            'table': table_name,
            'location': storage_desc.get('Location', ''),
            'input_format': storage_desc.get('InputFormat', ''),
            'output_format': storage_desc.get('OutputFormat', ''),
            'columns': columns,
            'partition_keys': partition_keys,
            'table_type': table.get('TableType', ''),
            'parameters': table.get('Parameters', {}),
        }

        return {'statusCode': 200, 'body': json.dumps(result)}

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'database': event.get('database_name', ''),
                'table': event.get('table_name', ''),
            }),
        }
