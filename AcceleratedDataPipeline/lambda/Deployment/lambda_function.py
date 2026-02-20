import json
import boto3
import os
import tempfile
import time
from bedrock_agentcore_starter_toolkit import Runtime

cognito_client = boto3.client('cognito-idp')
pool_id = os.environ.get('COGNITO_USER_POOL_ID')
websocket_api_url = os.environ.get('WEBSOCKET_API_URL')
temp_dir = '/tmp/my_mcp_folder'
os.makedirs(temp_dir, exist_ok=True) 
path = '/tmp/my_mcp_folder:'
os.chdir('/tmp')
os.environ['LD_LIBRARY_PATH'] = path + os.environ['LD_LIBRARY_PATH']
print(f"LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")

def send_websocket_message(connection_id, message):
    """Send message via WebSocket API"""
    if not connection_id:
        return
    
    try:
        apigateway_client = boto3.client('apigatewaymanagementapi', 
                                       endpoint_url=websocket_api_url)
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
    except Exception as e:
        print(f"WebSocket send error: {e}")

def get_cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

def lambda_handler(event, context):
    print(f"=== LAMBDA INVOKED ===")
    print(f"Full Event: {json.dumps(event, default=str)}")
    
    try:
        # Handle WebSocket routes
        route_key = event.get('requestContext', {}).get('routeKey')
        connection_id = event.get('requestContext', {}).get('connectionId')
        
        print(f"Route: {route_key}, Connection ID: {connection_id}")
        if route_key == '$connect':
            print("WebSocket connection established")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': '*'
                }
            }
        elif route_key == '$disconnect':
            print("WebSocket connection closed")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }
        elif route_key == 'deploy':
            print("Deploy route - processing deployment")
            return handle_deploy(event, context)
        elif route_key == 'generate' or route_key == '$default':
            print("Default route - processing message")
            if event.get('body'):
                try:
                    body = json.loads(event['body'])
                    print(f"Message body: {body}")
                    action = body.get('action')
                    print(f"Action: {action}")
                    
                    if action == 'deploy':
                        print("Deploy action detected in default route")
                        return handle_deploy(event, context)
                    else:
                        print(f"Unknown action: {action}")
                        send_websocket_message(connection_id, {
                            'status': 'UNKNOWN_ACTION',
                            'message': f'Unknown action: {action}'
                        })
                except Exception as e:
                    print(f"Error parsing body: {e}")
                    send_websocket_message(connection_id, {
                        'status': 'ERROR',
                        'message': f'Error parsing message: {str(e)}'
                    })
            return {'statusCode': 200, 'body': json.dumps({'message': 'Message received'})}
        else:
            print(f"Unknown route: {route_key}")
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': f'Unknown route: {route_key}'})
            }
    
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def handle_deploy(event, context):
    connection_id = None
    try:
        connection_id = event.get('requestContext', {}).get('connectionId')
        
        if 'body' in event and event['body']:
            body = json.loads(event['body'])
        else:
            body = event
        print(f"Received deploy body: {body}")
        
        # Get connection_id from body if not in request context
        if not connection_id:
            connection_id = body.get('connection_id')
        
        mcp_server_code = body.get('mcp_server_code')
        requirements_txt = body.get('requirements_txt')
        client_name = body.get('client_name', 'MCPServerClient')
        username = body.get('username')
        password = body.get('password')
        agent_name = body.get('agent_name', 'mcp_server_agentcore')
        
        if not all([mcp_server_code, requirements_txt, username, password, pool_id]):
            error_msg = 'Missing required parameters: mcp_server_code, requirements_txt, username, password'
            print(error_msg)
            send_websocket_message(connection_id, {
                'status': 'ERROR',
                'message': error_msg
            })
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': error_msg})
            }
        
        # Create temporary files
        print(f"Created temporary directory: {temp_dir}")   
        mcp_file = os.path.join(temp_dir, 'mcp_server.py')
        req_file = os.path.join(temp_dir, 'requirements.txt')
            
        with open(mcp_file, 'w') as f:
            f.write(mcp_server_code)
        
        with open(req_file, 'w') as f:
            f.write(requirements_txt)
        
        # Send initial status
        send_websocket_message(connection_id, {
            'status': 'STARTING',
            'message': 'Starting deployment process...'
        })
        
        # Create Cognito app client
        send_websocket_message(connection_id, {
            'status': 'CREATING_CLIENT',
            'message': 'Creating Cognito app client...'
        })
        
        client_response = cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=client_name,
            GenerateSecret=False,
            ExplicitAuthFlows=['ALLOW_USER_PASSWORD_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH']
        )
        client_id = client_response['UserPoolClient']['ClientId']
        
        # Authenticate user
        send_websocket_message(connection_id, {
            'status': 'AUTHENTICATING',
            'message': 'Authenticating user...'
        })
        
        auth_response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        print(f"Auth response: {auth_response}")
        bearer_token = auth_response['AuthenticationResult']['AccessToken']
        
        # Configure AgentCore Runtime
        boto_session = boto3.Session()
        region = boto_session.region_name or 'us-east-1'
        discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
        
        agentcore_runtime = Runtime()
        
        auth_config = {
            "customJWTAuthorizer": {
                "allowedClients": [client_id],
                "discoveryUrl": discovery_url,
            }
        }
        
        # Configure runtime
        send_websocket_message(connection_id, {
            'status': 'CONFIGURING',
            'message': 'Configuring AgentCore runtime...'
        })
        
        print('Creating the agentcore for entrypoint', mcp_file)
        response = agentcore_runtime.configure(
            entrypoint=mcp_file,
            auto_create_execution_role=True,
            auto_create_ecr=True,
            requirements_file=req_file,
            region=region,
            authorizer_configuration=auth_config,
            protocol="MCP",
            agent_name=agent_name
        )
        print(f"Configure response: {response}")
        
        # Launch runtime
        send_websocket_message(connection_id, {
            'status': 'LAUNCHING',
            'message': 'Launching AgentCore deployment...'
        })
        
        print('Launching the agentcore')
        launch_result = agentcore_runtime.launch()
        print(f"Launch result: {launch_result}")
        
        # Wait for status
        send_websocket_message(connection_id, {
            'status': 'MONITORING',
            'message': 'Monitoring deployment status...'
        })
        
        status_response = agentcore_runtime.status()
        status = status_response.endpoint['status']
        print(f"AgentCore Status: {status}")
        
        end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']
        timeout = 300  # 5 minutes timeout
        start_time = time.time()
        
        while status not in end_status and (time.time() - start_time) < timeout:
            # Send status update
            send_websocket_message(connection_id, {
                'status': 'IN_PROGRESS',
                'message': f'Deployment status: {status}',
                'deployment_status': status
            })
            
            time.sleep(10)
            status_response = agentcore_runtime.status()
            status = status_response.endpoint['status']
        
        # Store configuration
        send_websocket_message(connection_id, {
            'status': 'STORING_CONFIG',
            'message': 'Storing deployment configuration...'
        })
        
        ssm_client = boto3.client('ssm', region_name=region)
        secrets_client = boto3.client('secretsmanager', region_name=region)
        
        cognito_config = {
            'pool_id': pool_id,
            'client_id': client_id,
            'discovery_url': discovery_url,
            'bearer_token': bearer_token
        }
        
        try:
            secrets_client.create_secret(
                Name='mcp_server/cognito/credentials',
                Description='Cognito credentials for MCP server',
                SecretString=json.dumps(cognito_config)
            )
        except secrets_client.exceptions.ResourceExistsException:
            secrets_client.update_secret(
                SecretId='mcp_server/cognito/credentials',
                SecretString=json.dumps(cognito_config)
            )
        
        ssm_client.put_parameter(
            Name='/mcp_server/runtime/agent_arn',
            Value=launch_result.agent_arn,
            Type='String',
            Description='Agent ARN for MCP server',
            Overwrite=True
        )
        
        # Send final status
        send_websocket_message(connection_id, {
            'status': 'COMPLETED' if status == 'READY' else 'FAILED',
            'message': f'Deployment completed with status: {status}',
            'agent_arn': launch_result.agent_arn,
            'agent_id': launch_result.agent_id,
            'final_status': status
        })
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'agent_arn': launch_result.agent_arn,
                'agent_id': launch_result.agent_id,
                'status': status,
                'region': region,
                'cognito_config': {
                    'pool_id': pool_id,
                    'client_id': client_id,
                    'discovery_url': discovery_url
                }
            })
        }
    
    except Exception as e:
        print(f"Deployment error: {e}")
        
        # Send error status via WebSocket
        if not connection_id and 'body' in event and event['body']:
            try:
                body = json.loads(event['body'])
                connection_id = body.get('connection_id')
            except:
                pass
        
        send_websocket_message(connection_id, {
            'status': 'ERROR',
            'message': f'Deployment failed: {str(e)}',
            'error': str(e)
        })
        
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }
