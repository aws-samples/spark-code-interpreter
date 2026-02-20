import boto3
import json
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Lambda function for blueprint management."""
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {})
    
    try:
        # Parse body if it's a string
        if event.get('body'):
            body = json.loads(event['body'])
        else:
            body = event
        
        action = body.get('action')
        
        if not action:
            return cors_response(400, {'error': 'action is required'})
        
        if action == 'add':
            return add_blueprint(body)
        elif action == 'list':
            return list_blueprints()
        elif action == 'update':
            return update_blueprint(body)
        else:
            return cors_response(400, {'error': f'Unsupported action: {action}'})
    
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Return response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body)
    }

def list_records(table, limit=None):
    """List records from DynamoDB table."""
    try:
        params = {}
        if limit:
            params['Limit'] = limit
        
        response = table.scan(**params)
        return cors_response(200, {
            'items': response['Items'],
            'count': response['Count']
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def get_record(table, key):
    """Get single record from DynamoDB table."""
    try:
        if not key:
            return cors_response(400, {'error': 'key is required'})
        
        response = table.get_item(Key=key)
        return cors_response(200 if 'Item' in response else 404, {
            'item': response.get('Item'),
            'found': 'Item' in response
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def add_blueprint(data):
    """Add blueprint to DynamoDB table."""
    try:
        required_fields = ['name', 'description', 'category']
        for field in required_fields:
            if not data.get(field):
                return cors_response(400, {'error': f'{field} is required'})
        
        table = dynamodb.Table('blueprints')
        
        item = {
            'tool_id': data.get('tool_id'),
            'name': data['name'],
            'description': data['description'],
            'category': data['category']
        }
        
        if 'service_type' in data:
            item['service_type'] = data['service_type']
        if 'actions' in data:
            item['actions'] = data['actions']
        if 'prompt' in data:
            item['prompt'] = data['prompt']
        if 'code' in data:
            item['code'] = data['code']
        
        table.put_item(Item=item)
        return cors_response(201, {
            'message': 'Blueprint added successfully'
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def list_blueprints():
    """List all blueprints from DynamoDB table."""
    try:
        table = dynamodb.Table('blueprints')
        response = table.scan()
        return cors_response(200, {
            'items': response['Items'],
            'count': response['Count']
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def update_blueprint(data):
    """Update blueprint in DynamoDB table."""
    try:
        if not data.get('key') or not data.get('item'):
            return cors_response(400, {'error': 'key and item are required'})
        
        table = dynamodb.Table('blueprints')
        key = data['key']
        item = data['item']
        
        # Build update expression
        update_expression = 'SET '
        expression_values = {}
        
        for field, value in item.items():
            update_expression += f'{field} = :{field}, '
            expression_values[f':{field}'] = value
        
        update_expression = update_expression.rstrip(', ')
        
        response = table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return cors_response(200, {
            'message': 'Blueprint updated successfully',
            'item': response['Attributes']
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def update_record(table, key, update_expression, expression_values):
    """Update record in DynamoDB table."""
    try:
        if not key or not update_expression:
            return cors_response(400, {'error': 'key and update_expression are required'})
        
        params = {
            'Key': key,
            'UpdateExpression': update_expression,
            'ReturnValues': 'ALL_NEW'
        }
        if expression_values:
            params['ExpressionAttributeValues'] = expression_values
        
        response = table.update_item(**params)
        return cors_response(200, {
            'message': 'Record updated successfully',
            'item': response['Attributes']
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def delete_record(table, key):
    """Delete record from DynamoDB table."""
    try:
        if not key:
            return cors_response(400, {'error': 'key is required'})
        
        response = table.delete_item(
            Key=key,
            ReturnValues='ALL_OLD'
        )
        return cors_response(200, {
            'message': 'Record deleted successfully',
            'deleted_item': response.get('Attributes')
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})