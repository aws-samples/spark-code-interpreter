import json
import boto3
from botocore.exceptions import ClientError
import traceback

def list_lambda_functions():
    """List all Lambda functions"""
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.list_functions()
        
        functions = []
        for function in response['Functions']:
            functions.append({
                'name': function['FunctionName'],
                'arn': function['FunctionArn'],
                'runtime': function.get('Runtime', 'N/A'),
                'lastModified': function.get('LastModified', 'N/A'),
                'description': function.get('Description', 'N/A')
            })
        
        print(f"Found {len(functions)} Lambda functions")
        return functions
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Lambda ClientError - Code: {error_code}, Message: {error_message}")
        raise Exception(f"Failed to list Lambda functions ({error_code}): {error_message}")
    except Exception as e:
        print(f"Unexpected error in list_lambda_functions: {str(e)}")
        raise Exception(f"Lambda listing error: {str(e)}")

def list_rest_apis():
    """List all REST APIs"""
    try:
        client = boto3.client('apigateway')
        response = client.get_rest_apis()
        
        apis = []
        if 'items' in response:
            for api in response['items']:
                apis.append({
                    'name': api['name'],
                    'id': api['id'],
                    'description': api.get('description', 'N/A'),
                    'createdDate': str(api['createdDate']),
                    'version': api.get('version', 'N/A')
                })
        
        print(f"Found {len(apis)} REST APIs")
        return apis
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"API Gateway ClientError - Code: {error_code}, Message: {error_message}")
        raise Exception(f"Failed to list REST APIs ({error_code}): {error_message}")
    except Exception as e:
        print(f"Unexpected error in list_rest_apis: {str(e)}")
        raise Exception(f"REST API listing error: {str(e)}")

def lambda_handler(event, context):
    print("=== LIST RESOURCES LAMBDA STARTED ===")
    print(f"Raw event: {json.dumps(event, default=str)}")
    
    try:
        if 'body' in event and event['body']:
            print(f"Parsing body: {event['body']}")
            body = json.loads(event['body'])
        else:
            print("Using event as body")
            body = event
        
        print(f"Parsed request body: {body}")
        
        action = body.get('action')
        
        if action == 'list_lambda':
            try:
                functions = list_lambda_functions()
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'functions': functions,
                        'count': len(functions)
                    })
                }
            except Exception as e:
                print(f"Lambda listing failed: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'error': str(e)
                    })
                }
                
        elif action == 'list_restapi':
            try:
                apis = list_rest_apis()
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'apis': apis,
                        'count': len(apis)
                    })
                }
            except Exception as e:
                print(f"REST API listing failed: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'error': str(e)
                    })
                }
        else:
            print(f"Unknown action received: {action}")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'error': f'Unknown action: {action}. Supported actions: list_lambda, list_restapi'
                })
            }
    
    except Exception as e:
        print(f"LAMBDA ERROR: {str(e)}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'error': f'Unexpected error: {str(e)}'
            })
        }