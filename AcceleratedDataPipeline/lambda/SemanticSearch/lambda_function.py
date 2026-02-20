import json
import boto3
from botocore.exceptions import ClientError
import traceback
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Initialize clients
cognito_client = boto3.client('cognito-idp')

def get_cognito_access_token(client_name, username, password, pool_id):
    print("Starting Cognito authentication")
    try:
        print(f"Creating client with pool_id: {pool_id}, client_name: {client_name}")
        client_response = cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=client_name,
            GenerateSecret=False,
            ExplicitAuthFlows=['ALLOW_USER_PASSWORD_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH']
        )
        client_id = client_response['UserPoolClient']['ClientId']
        print(f"Client created successfully. Client ID: {client_id}")
        
        print(f"Authenticating user: {username}")
        auth_response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        print("Authentication successful")
        
        boto_session = boto3.Session()
        region = boto_session.region_name or 'us-east-1'
        discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
        print(f"Discovery URL: {discovery_url}")
        
        auth_config = {
            "customJWTAuthorizer": {
                "allowedClients": [client_id],
                "discoveryUrl": discovery_url,
            }
        }
        access_token = auth_response['AuthenticationResult']['AccessToken']
        print(f"Access token obtained: {access_token[:20]}...")
        return auth_config, access_token
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Cognito ClientError - Code: {error_code}, Message: {error_message}")
        raise Exception(f"Cognito authentication failed ({error_code}): {error_message}")
    except KeyError as e:
        print(f"KeyError in auth response: {str(e)}")
        raise Exception(f"Missing key in authentication response: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in get_cognito_access_token: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"Cognito authentication error: {str(e)}")

def list_gateway(client):
    print("Listing gateways")
    try:
        response = client.list_gateways()
        return response['items']
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Bedrock ClientError - Code: {error_code}, Message: {error_message}")
        raise Exception(f"AWS Bedrock gateway list failed ({error_code}): {error_message}")

def onboard_lambda(client, gateway_identifier, target_name, inlinePayload, credential_provider_config=None):
    try:
        print(f"Onboarding Lambda to gateway: {gateway_identifier}")
        response = client.create_gateway_target(
                    gatewayIdentifier=gateway_identifier,
                    name=target_name,
                    targetConfiguration=inlinePayload,
                    credentialProviderConfigurations=credential_provider_config
        )
        print(f"Lambda onboarded successfully: {response}")
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Bedrock ClientError - Code: {error_code}, Message: {error_message}")
        raise Exception(f"Lambda onboarding failed ({error_code}): {error_message}")
    except Exception as e:
        print(f"Unexpected error in onboard_lambda: {str(e)}")
        raise Exception(f"Lambda onboarding error: {str(e)}")



def create_gateway(client,gateway_name, authorizer_config, role_arn, authorizer_type,protocol_type="MCP",):
    try:
        print(f"Creating Bedrock gateway with name: {gateway_name}, {authorizer_type},{authorizer_config}")
        if authorizer_type == "CUSTOM_JWT":
            gateway_params = {
                'name': gateway_name,
                'protocolType': protocol_type,
                'roleArn': role_arn,
                'authorizerType': authorizer_type,
                'authorizerConfiguration': authorizer_config,
                'exceptionLevel': 'DEBUG',
                "protocolConfiguration": {
                    "mcp": {
                        "searchType": "SEMANTIC"
                    }
                }

            }
        else:
            gateway_params = {
                'name': gateway_name,
                'roleArn': role_arn,
                'protocolType': protocol_type,
                'protocolConfiguration': {
                    "mcp": {
                        "searchType": "SEMANTIC"
                    }
                },
                'authorizerType': 'AWS_IAM'
            }

        print(f"Gateway parameters: {json.dumps(gateway_params, default=str)}")
        
        response = client.create_gateway(**gateway_params)
        print(f"Gateway created successfully: {json.dumps(response, default=str)}")
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Bedrock ClientError - Code: {error_code}, Message: {error_message}")
        raise Exception(f"AWS Bedrock gateway creation failed ({error_code}): {error_message}")
    except Exception as e:
        print(f"Unexpected error in create_gateway: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"Gateway creation error: {str(e)}")

async def search_tools(gateway_url, access_token, query):
     """Search for tools using semantic search"""
     try:
         print(f"Searching tools with query: {query}")
         headers = {"Authorization": f"Bearer {access_token}"}
         async with streamablehttp_client(gateway_url, headers=headers) as (read, write, _):
             async with ClientSession(read, write) as session:
                 await session.initialize()
                 
                 # Use the built-in search tool
                 response = await session.call_tool(
                     "x_amz_bedrock_agentcore_search",
                     arguments={"query": query}
                 )
                 
                 # Parse the search results
                 results = []
                 for content in response.content:
                     tools = json.loads(content.text)
                     results.extend(tools)
                 
                 print(f"Found {len(results)} relevant tools for: {query}")
                 return results
                 
     except Exception as e:
         print(f"Search tools error: {str(e)}")
         raise Exception(f"Tool search failed: {str(e)}")

def lambda_handler(event, context):
    print("=== LAMBDA FUNCTION STARTED ===")
    print(f"Raw event: {json.dumps(event, default=str)}")
    #print(f"Lambda execution role ARN: {context.invoked_function_arn}")
    
    # Extract role ARN from function ARN
    lambda_role_arn = "arn:aws:iam::905418369822:role/gateway-default-role"
       
    try:
        if 'body' in event and event['body']:
            print(f"Parsing body: {event['body']}")
            body = json.loads(event['body'])
        else:
            print("Using event as body")
            body = event
        
        print(f"Parsed request body: {body}")

        action = body.get('action')
        
        # Only extract Cognito parameters for actions that need them
        if action == 'create_gateway':
            username = body.get('client_id')
            password = body.get('client_secret')
            client_name = body.get('client_name')
            pool_id = body.get('cognito_domain')
            authorizer_type = body.get('authorizer_type')
        
        client = boto3.client('bedrock-agentcore-control')
        if action == 'create_gateway':
            if not all([username, password, pool_id, client_name]):
                missing = [param for param, value in [('client_id', username), ('client_secret', password), ('cognito_domain', pool_id), ('client_name', client_name)] if not value]
                print(f"Missing parameters: {missing}")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'error': f'Missing required parameters: {", ".join(missing)}'
                    })
                }
            
            if not client_name:
                print("Missing client_name parameter")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                     },
                    'body': json.dumps({
                        'error': 'Missing required parameter: client_name'
                    })
                }
            
            try:
                print("Getting access token....")
                authorizer_config, access_token = get_cognito_access_token(client_name, username, password, pool_id)
                print("Access token received successfully")
            except Exception as e:
                print(f"Authentication failed: {str(e)}")
                return {
                    'statusCode': 401,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                     },
                    'body': json.dumps({
                        'error': str(e)
                    })
                }
            
            print("Creating gateway....")
            gateway_name = client_name
            
            try:
                print("Creating gateway.... by calling function")
                gateway_response = create_gateway(
                    client=client,
                    gateway_name=gateway_name,
                    authorizer_config=authorizer_config,
                    role_arn=lambda_role_arn,
                    authorizer_type=authorizer_type
                )
                print("Gateway creation completed successfully",gateway_response)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                     },
                    'body': json.dumps({
                        'access_token': access_token,
                        'gateway': {
                            'name': gateway_response.get('name'),
                            'gatewayArn': gateway_response.get('gatewayArn')
                        }
                    })
                }
            except Exception as e:
                print(f"Gateway creation failed: {str(e)}")
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
        elif action == 'search':
             gateway_id = body.get('gateway_id')
             query = body.get('query')
             
             if not all([gateway_id, query]):
                 missing = [param for param, value in [('gateway_id', gateway_id), ('query', query)] if not value]
                 return {
                     'statusCode': 400,
                     'headers': {
                         'Access-Control-Allow-Origin': '*',
                         'Access-Control-Allow-Headers': 'Content-Type'
                     },
                     'body': json.dumps({
                         'error': f'Missing required parameters: {", ".join(missing)}'
                     })
                 }
             
             try:
                 print("Getting access token for search....")
                 _, access_token = get_cognito_access_token(f"search-{gateway_id}", username, password, pool_id)
                 
                 gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
                 print(f"Searching tools at: {gateway_url}")
                 
                 search_results = asyncio.run(search_tools(gateway_url, access_token, query))
                 print(f"Search results: {search_results}")
                 return {
                     'statusCode': 200,
                     'headers': {
                         'Access-Control-Allow-Origin': '*',
                         'Access-Control-Allow-Headers': 'Content-Type'
                     },
                     'body': json.dumps({
                         'results': search_results
                     })
                 }
             except Exception as e:
                 print(f"Search failed: {str(e)}")
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
        elif action == 'onboard_lambda':
            gateway_identifier = body.get('gatewayIdentifier')
            target_name = body.get('name')
            inlinePayload = body.get('targetConfiguration')
            credential_provider_config = body.get('credentialProviderConfigurations')
            print(f'credential_provider_config, {credential_provider_config}')
            print(f'inlinePayload, {inlinePayload}')
            
            if not all([gateway_identifier, target_name, inlinePayload]):
                missing = [param for param, value in [('gateway_identifier', gateway_identifier), ('target_name', target_name), ('inlinePayload', inlinePayload)] if not value]
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'error': f'Missing required parameters: {", ".join(missing)}'
                    })
                }
            
            try:
                onboard_response = onboard_lambda(
                    client=client,
                    gateway_identifier=gateway_identifier,
                    target_name=target_name,
                    inlinePayload=inlinePayload,
                    credential_provider_config=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
                )
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'target': {
                            'name': onboard_response.get('name'),
                            'targetArn': onboard_response.get('targetArn')
                        }
                    })
                }
            except Exception as e:
                print(f"Lambda onboarding failed: {str(e)}")
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
        elif action == 'list_gateway':
            try:
                print("Listing gateway....")
                gateway_response = list_gateway(client)
                print("Gateway listing completed successfully", len(gateway_response))

                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type'
                     },
                    'body': json.dumps(gateway_response, default=str)
                }
            except Exception as e:
                print(f"Gateway listing failed: {str(e)}")
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
                    'error': f'Unknown action: {action}'
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