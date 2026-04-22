"""MCP Tool: execute_spark_on_lambda
Execute validated PySpark code on AWS Lambda (Spark-on-Lambda).
"""

import json
import boto3
from botocore.config import Config


def lambda_handler(event, context):
    try:
        spark_code = event['spark_code']
        s3_output_path = event['s3_output_path']
        lambda_function = event['lambda_function']
        s3_bucket = event['s3_bucket']
        spark_config = event.get('spark_config', {})
        region = event.get('region', 'us-east-1')
        session_id = event.get('session_id', '')

        from progress import update_progress
        update_progress(s3_bucket, session_id, "execute_spark_on_lambda", "running", "Executing PySpark on Lambda...", region)

        lambda_client = boto3.client(
            'lambda',
            region_name=region,
            config=Config(read_timeout=320, connect_timeout=10),
        )

        payload = {
            'code': spark_code,
            'bucket': s3_bucket.replace('s3://', '').split('/')[0],
            'file_path': s3_output_path.replace(f's3://{s3_bucket}/', '') if s3_output_path else '',
            'iterate': 0,
            'config': spark_config,
        }

        response = lambda_client.invoke(
            FunctionName=lambda_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
        )

        result = json.loads(response['Payload'].read())

        if 'body' in result:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
        else:
            body = result

        actual_s3_output_path = body.get('s3_output_path', s3_output_path)
        lambda_status = 'success' if result.get('statusCode') == 200 else 'error'

        tool_result = {
            'status': lambda_status,
            'execution_platform': 'lambda',
            's3_output_path': actual_s3_output_path,
            'result': body,
            'lambda_function': lambda_function,
        }

        update_progress(s3_bucket, session_id, "execute_spark_on_lambda", "complete" if lambda_status == "success" else "error", f"Lambda execution {lambda_status}", region)
        return {'statusCode': 200, 'body': json.dumps(tool_result)}

    except Exception as e:
        from progress import update_progress
        update_progress(event.get('s3_bucket', ''), event.get('session_id', ''), "execute_spark_on_lambda", "error", str(e), event.get('region', 'us-east-1'))
        return {'statusCode': 500, 'body': json.dumps({'status': 'error', 'execution_platform': 'lambda', 'error': str(e)})}
