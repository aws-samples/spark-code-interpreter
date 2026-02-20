import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    route_key = event.get('requestContext', {}).get('routeKey')
    
    if route_key == '$connect':
        return {'statusCode': 200}
    elif route_key == '$disconnect':
        return {'statusCode': 200}
    elif route_key == 'generate_prompt':
        return handle_generate_prompt(event)
    elif route_key == 'generate_mcp_tool':
        return handle_generate_mcp_tool(event)
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid route'})
        }

def handle_generate_prompt(event):
    try:
        if 'body' in event and event['body']:
            body = json.loads(event['body'])
            service = body.get('service', '')
            actions = body.get('actions', [])
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Missing service or actions'})
            }
        
        prompt = f"""
        Generate a detailed prompt for creating an MCP tool for {service} with the following actions: {', '.join(actions)}.
        
        The prompt should include:
        - Clear description of the tool's purpose
        - Specific implementation requirements
        - Function signatures and parameters
        - Error handling guidelines
        - Usage examples
        
        Make it comprehensive and actionable for developers.
        """
        
        return stream_bedrock_response(event, prompt)
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_generate_mcp_tool(event):
    try:
        if 'body' in event and event['body']:
            body = json.loads(event['body'])
            service = body.get('service', '')
            actions = body.get('actions', [])
            language = body.get('language', 'python')
            custom_prompt = body.get('prompt', '')
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = f"""
            Generate a complete MCP tool in {language} for {service} with the following actions: {', '.join(actions)}.
            
            Requirements:
            - Use proper MCP framework structure
            - Include all necessary imports
            - Implement error handling
            - Add proper documentation
            - Follow {language} best practices
            - Include usage examples
            
            Generate ONLY the code without explanations.
            """
        
        return stream_bedrock_response(event, prompt)
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def stream_bedrock_response(event, prompt):
    try:
        connection_id = event['requestContext']['connectionId']
        
        apigateway_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url='https://bb4bk15ec3.execute-api.us-east-1.amazonaws.com/production'
        )
        
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        response = bedrock.invoke_model_with_response_stream(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 4000,
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }]
            })
        )
        
        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            if chunk['type'] == 'content_block_delta' and chunk['delta']['text']:
                apigateway_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        'type': 'content_block_delta',
                        'delta': {'text': chunk['delta']['text']}
                    })
                )
        
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}})
        )
        
        return {'statusCode': 200}
        
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }