    import json
    import boto3
    import os
    from decimal import Decimal

    client = boto3.client('dynamodb')
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'deployment_info')

    def decimal_default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError

    def get_cors_headers():
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        }

    def convert_to_dynamodb_item(data):
        item = {}
        for key, value in data.items():
            if isinstance(value, str):
                item[key] = {'S': value}
            elif isinstance(value, (int, float)):
                item[key] = {'N': str(value)}
            elif isinstance(value, bool):
                item[key] = {'BOOL': value}
            elif isinstance(value, list):
                item[key] = {'L': [convert_to_dynamodb_item({'item': item})['item'] for item in value]}
            elif isinstance(value, dict):
                item[key] = {'M': convert_to_dynamodb_item(value)}
            elif value is None:
                item[key] = {'NULL': True}
        return item

    def convert_from_dynamodb_item(item):
        data = {}
        for key, value in item.items():
            if 'S' in value:
                data[key] = value['S']
            elif 'N' in value:
                data[key] = float(value['N']) if '.' in value['N'] else int(value['N'])
            elif 'BOOL' in value:
                data[key] = value['BOOL']
            elif 'L' in value:
                data[key] = [convert_from_dynamodb_item({'item': item})['item'] for item in value['L']]
            elif 'M' in value:
                data[key] = convert_from_dynamodb_item(value['M'])
            elif 'NULL' in value:
                data[key] = None
        return data

    def lambda_handler(event, context):
        try:
            if event.get('httpMethod') == 'OPTIONS':
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'message': 'CORS preflight'})
                }
            
            if 'body' in event and event['body']:
                body = json.loads(event['body'])
            else:
                body = event
            
            action = body.get('action')
            
            if action == 'store':
                return store_deployment(body)
            elif action == 'update':
                return update_deployment(body)
            elif action == 'delete':
                return delete_deployment(body)
            elif action == 'get':
                return get_deployment(body)
            elif action == 'list':
                return list_deployments(body)
            elif action == 'search':
                return search_deployments(body)
            else:
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'error': 'Invalid action'})
                }
        
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': str(e)})
            }

    def store_deployment(event):
        try:
            deployment_info = event.get('deployment_info', event)
            item = convert_to_dynamodb_item(deployment_info)
            
            response = client.put_item(
                TableName=table_name,
                Item=item
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': 'Deployment stored successfully', 'deployment_uuid': deployment_info['deployment_uuid']})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Failed to store deployment: {str(e)}'})
            }

    def update_deployment(event):
        try:
            deployment_uuid = event['deployment_uuid']
            updates = event['updates']
            
            update_expression = "SET "
            expression_values = {}
            expression_names = {}
            
            for key, value in updates.items():
                if key != 'deployment_uuid':
                    attr_name = f"#{key}"
                    attr_value = f":{key}"
                    update_expression += f"{attr_name} = {attr_value}, "
                    expression_names[attr_name] = key
                    
                    if isinstance(value, str):
                        expression_values[attr_value] = {'S': value}
                    elif isinstance(value, (int, float)):
                        expression_values[attr_value] = {'N': str(value)}
                    elif isinstance(value, bool):
                        expression_values[attr_value] = {'BOOL': value}
                    elif value is None:
                        expression_values[attr_value] = {'NULL': True}
            
            update_expression = update_expression.rstrip(', ')
            
            response = client.update_item(
                TableName=table_name,
                Key={'deployment_uuid': {'S': deployment_uuid}},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': 'Deployment updated successfully', 'item': convert_from_dynamodb_item(response['Attributes'])})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Failed to update deployment: {str(e)}'})
            }

    def delete_deployment(event):
        try:
            deployment_uuid = event['deployment_uuid']
            
            response = client.delete_item(
                TableName=table_name,
                Key={'deployment_uuid': {'S': deployment_uuid}}
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': 'Deployment deleted successfully'})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Failed to delete deployment: {str(e)}'})
            }

    def get_deployment(event):
        try:
            deployment_uuid = event['deployment_uuid']
            
            response = client.get_item(
                TableName=table_name,
                Key={'deployment_uuid': {'S': deployment_uuid}}
            )
            
            if 'Item' in response:
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'item': convert_from_dynamodb_item(response['Item'])})
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'error': 'Deployment not found'})
                }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Failed to get deployment: {str(e)}'})
            }

    def list_deployments(event):
        try:
            response = client.scan(TableName=table_name)
            
            items = [convert_from_dynamodb_item(item) for item in response['Items']]
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'items': items})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Failed to list deployments: {str(e)}'})
            }

    def search_deployments(event):
        try:
            search_params = event.get('search_params', {})
            
            if not search_params:
                return list_deployments(event)
            
            filter_expression = ""
            expression_values = {}
            expression_names = {}
            
            for i, (key, value) in enumerate(search_params.items()):
                attr_name = f"#attr{i}"
                attr_value = f":val{i}"
                
                if i > 0:
                    filter_expression += " AND "
                
                if isinstance(value, str):
                    filter_expression += f"contains({attr_name}, {attr_value})"
                    expression_values[attr_value] = {'S': value}
                else:
                    filter_expression += f"{attr_name} = {attr_value}"
                    if isinstance(value, (int, float)):
                        expression_values[attr_value] = {'N': str(value)}
                    elif isinstance(value, bool):
                        expression_values[attr_value] = {'BOOL': value}
                
                expression_names[attr_name] = key
            
            response = client.scan(
                TableName=table_name,
                FilterExpression=filter_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            items = [convert_from_dynamodb_item(item) for item in response['Items']]
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'items': items})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Failed to search deployments: {str(e)}'})
            }