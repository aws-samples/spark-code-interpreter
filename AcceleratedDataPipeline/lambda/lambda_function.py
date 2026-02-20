import boto3
import json
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Lambda function for DynamoDB CRUD operations."""
    try:
        action = event.get('action')
        table_name = event.get('table_name')
        
        if not action or not table_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'action and table_name are required'})
            }
        
        table = dynamodb.Table(table_name)
        
        if action == 'list':
            return list_records(table, event.get('limit'))
        elif action == 'get':
            return get_record(table, event.get('key'))
        elif action == 'add':
            return add_record(table, event.get('item'))
        elif action == 'update':
            return update_record(table, event.get('key'), event.get('update_expression'), event.get('expression_values'))
        elif action == 'delete':
            return delete_record(table, event.get('key'))
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unsupported action: {action}'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def list_records(table, limit=None):
    """List records from DynamoDB table."""
    try:
        params = {}
        if limit:
            params['Limit'] = limit
        
        response = table.scan(**params)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'items': response['Items'],
                'count': response['Count']
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_record(table, key):
    """Get single record from DynamoDB table."""
    try:
        if not key:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'key is required'})
            }
        
        response = table.get_item(Key=key)
        return {
            'statusCode': 200 if 'Item' in response else 404,
            'body': json.dumps({
                'item': response.get('Item'),
                'found': 'Item' in response
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def add_record(table, item):
    """Add record to DynamoDB table."""
    try:
        if not item:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'item is required'})
            }
        
        table.put_item(Item=item)
        return {
            'statusCode': 201,
            'body': json.dumps({
                'message': 'Record added successfully',
                'item': item
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def update_record(table, key, update_expression, expression_values):
    """Update record in DynamoDB table."""
    try:
        if not key or not update_expression:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'key and update_expression are required'})
            }
        
        params = {
            'Key': key,
            'UpdateExpression': update_expression,
            'ReturnValues': 'ALL_NEW'
        }
        if expression_values:
            params['ExpressionAttributeValues'] = expression_values
        
        response = table.update_item(**params)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Record updated successfully',
                'item': response['Attributes']
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def delete_record(table, key):
    """Delete record from DynamoDB table."""
    try:
        if not key:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'key is required'})
            }
        
        response = table.delete_item(
            Key=key,
            ReturnValues='ALL_OLD'
        )
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Record deleted successfully',
                'deleted_item': response.get('Attributes')
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }