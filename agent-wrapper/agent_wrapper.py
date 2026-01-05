import json
import boto3
import os
import logging
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Bedrock AgentCore client
agent_core_client = boto3.client('bedrock-agentcore', region_name='us-east-1', config=boto3.session.Config(
        read_timeout=300,
        connect_timeout=60,
        retries={'max_attempts': 3}
    ))

# Agent ARN from environment variable
AGENT_ARN = os.environ.get('AGENT_ARN', 'arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu')

def lambda_handler(event, context):
    """
    Wrapper Lambda that accepts natural language queries and invokes Spark Supervisor Agent
    
    Input formats supported:
    1. Direct: {"prompt": "what is 5+5"}
    2. API Gateway: {"body": "{\"prompt\": \"what is 5+5\"}"}
    3. Alternative: {"query": "what is 5+5"}
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        logger.info(f"Event keys: {list(event.keys())}")
        logger.info(f"Event type: {type(event)}")
        
        # Extract prompt from various input formats
        prompt = None
        
        # Check if it's from API Gateway (has 'body')
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            prompt = body.get('prompt') or body.get('query') or body.get('question')
        else:
            # Direct invocation
            prompt = event.get('prompt') or event.get('query') or event.get('question')
        
        if not prompt:
            logger.error("No prompt provided in request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing prompt parameter',
                    'usage': 'Provide "prompt", "query", or "question" in request body'
                })
            }
        
        logger.info(f"Processing prompt: {prompt}")
        logger.info(f"Invoking agent: {AGENT_ARN}")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Session ID: {session_id}")
        
        # Configure S3 paths with session-based structure
        s3_bucket = os.environ.get('S3_BUCKET', 'spark-data-817323390093-us-east-1')
        s3_session_path = f"{session_id}"
        s3_output_path = f"s3://{s3_bucket}/{session_id}/output/"
        
        # Get Lambda ARN and extract function name
        lambda_arn = os.environ.get('SPARK_LAMBDA_ARN', 'arn:aws:lambda:us-east-1:817323390093:function:dev-spark-on-lambda')
        lambda_function = lambda_arn.split(':')[-1] if lambda_arn else 'dev-spark-on-lambda'
        
        # Prepare payload - agent expects 'prompt', 'session_id', and 'config'
        payload_dict = {
            'prompt': prompt,
            'session_id': session_id,
            's3_output_path': s3_output_path,  # Tell agent where to write results
            'config': {
                'model_id': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                'bedrock_model': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                'bedrock_region': 'us-east-1',
                'lambda_function': lambda_function,
                'lambda_arn': lambda_arn,
                's3_bucket': s3_bucket,
                's3_output_path': s3_output_path,
                'code_gen_agent_arn': os.environ.get('CODE_GEN_ARN', 'arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/ray_code_interpreter-FKoWFR2k9A'),
                'emr_application_id': os.environ.get('EMR_APP_ID', ''),
                'emr_execution_role_arn': os.environ.get('EMR_ROLE_ARN', ''),
                'region': 'us-east-1',
                # Spark configuration for S3 access
                'spark_config': {
                    'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
                    'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
                    'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
                }
            }
        }
        payload = json.dumps(payload_dict).encode()
        
        logger.info(f"Payload: {json.dumps(payload_dict, indent=2)}")
        
        # Invoke agent
        try:
            response = agent_core_client.invoke_agent_runtime(
                agentRuntimeArn=AGENT_ARN,
                runtimeSessionId=session_id,
                payload=payload
            )
            
            logger.info("Agent invoked successfully")
            
            # Read the streaming response
            result_text = response['response'].read().decode('utf-8')
            
            logger.info(f"Agent response: {result_text[:200]}...")
            
            # Parse and clean the response
            try:
                # The agent returns a JSON string, parse it
                agent_response = json.loads(result_text)
                
                # Handle double-encoded JSON (string within string)
                while isinstance(agent_response, str):
                    logger.info(f"Response is still a string, parsing again...")
                    agent_response = json.loads(agent_response)
                
                # Ensure agent_response is a dict
                if not isinstance(agent_response, dict):
                    logger.warning(f"Agent response is not a dict after parsing, type: {type(agent_response)}")
                    agent_response = {'raw_response': str(agent_response)}
                
                logger.info(f"Parsed agent response keys: {list(agent_response.keys())}")
                
                # Extract only the essential information
                actual_results = agent_response.get('actual_results', [])
                
                # Ensure data is a list
                if isinstance(actual_results, str):
                    # If it's a string, try to parse it as JSON
                    try:
                        actual_results = json.loads(actual_results)
                    except:
                        actual_results = []
                
                clean_response = {
                    'status': 'success',
                    'data': actual_results if isinstance(actual_results, list) else [],
                    's3_path': agent_response.get('s3_output_path', ''),
                    'execution_status': agent_response.get('execution_result', 'unknown'),
                    'message': agent_response.get('execution_message', ''),
                    'session_id': session_id
                }
                
                data_count = len(clean_response['data']) if isinstance(clean_response['data'], list) else 0
                logger.info(f"Cleaned response - Data rows: {data_count}, S3 path: {clean_response['s3_path']}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps(clean_response),
                    'headers': {
                        'Content-Type': 'application/json'
                    }
                }
                
            except json.JSONDecodeError as parse_error:
                # If parsing fails, return the raw response for debugging
                logger.warning(f"Failed to parse agent response as JSON: {parse_error}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'raw_result': result_text,
                        'prompt': prompt,
                        'session_id': session_id,
                        'note': 'Response could not be parsed, returning raw output'
                    }),
                    'headers': {
                        'Content-Type': 'application/json'
                    }
                }
            
        except Exception as e:
            logger.error(f"Failed to invoke agent: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to invoke agent',
                    'details': str(e)
                })
            }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
