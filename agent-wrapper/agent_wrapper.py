import json
import boto3
import os
import logging
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Bedrock AgentCore client
agent_core_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

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
        
        # Prepare payload - agent expects 'prompt', 'session_id', and 'config'
        payload_dict = {
            'prompt': prompt,
            'session_id': session_id,
            's3_output_path': s3_output_path,  # Tell agent where to write results
            'config': {
                'model_id': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                'bedrock_model': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                'bedrock_region': 'us-east-1',
                'lambda_function': 'dev-spark-on-lambda',
                'lambda_arn': os.environ.get('SPARK_LAMBDA_ARN', 'arn:aws:lambda:us-east-1:817323390093:function:dev-spark-on-lambda'),
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
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'result': result_text,
                    'prompt': prompt,
                    'sessionId': session_id
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
