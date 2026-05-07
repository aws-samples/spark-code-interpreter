"""MCP Tool: execute_spark_on_emr
Execute validated PySpark code on EMR Serverless.
"""

import json
import time
import os
import boto3


def lambda_handler(event, context):
    try:
        spark_code = event['spark_code']
        s3_output_path = event['s3_output_path']
        s3_bucket = event['s3_bucket']
        session_id = event['session_id']
        emr_application_id = event['emr_application_id']
        emr_execution_role_arn = event.get('emr_execution_role_arn', '')
        emr_timeout_minutes = event.get('emr_timeout_minutes', 15)
        jdbc_driver_path = event.get('jdbc_driver_path', '')
        region = event.get('region', 'us-east-1')

        s3_client = boto3.client('s3', region_name=region)
        emr_client = boto3.client('emr-serverless', region_name=region)

        from progress import update_progress
        update_progress(s3_bucket, session_id, "execute_spark_on_emr", "running", "Submitting job to EMR Serverless...", region)

        # Save validated code to S3 for backend retrieval
        if session_id and s3_bucket:
            code_key = f"{session_id}/{session_id}_code.py"
            s3_client.put_object(Bucket=s3_bucket, Key=code_key, Body=spark_code.encode('utf-8'))

        # Upload script to S3
        script_key = f"scripts/spark_script_{int(time.time())}.py"
        s3_client.put_object(Bucket=s3_bucket, Key=script_key, Body=spark_code.encode('utf-8'))
        script_path = f"s3://{s3_bucket}/{script_key}"

        # Build spark-submit parameters
        spark_params = '--conf spark.executor.memory=4g --conf spark.executor.cores=2'
        if jdbc_driver_path:
            spark_params += f' --jars {jdbc_driver_path}'

        # Resolve EMR execution role if not provided
        if not emr_execution_role_arn:
            sts_client = boto3.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
            # Use the CloudFormation-created role name pattern
            env = os.environ.get('ENVIRONMENT', 'dev')
            emr_execution_role_arn = f"arn:aws:iam::{account_id}:role/{env}-spark-emr-execution-role"

        # Start EMR job
        response = emr_client.start_job_run(
            applicationId=emr_application_id,
            executionRoleArn=emr_execution_role_arn,
            jobDriver={
                'sparkSubmit': {
                    'entryPoint': script_path,
                    'sparkSubmitParameters': spark_params,
                }
            },
            configurationOverrides={
                'monitoringConfiguration': {
                    's3MonitoringConfiguration': {
                        'logUri': f"s3://{s3_bucket}/logs/emr/"
                    },
                    'cloudWatchLoggingConfiguration': {'enabled': True},
                }
            },
        )

        job_run_id = response['jobRunId']

        # Wait for job completion
        timeout = emr_timeout_minutes * 60
        start_time = time.time()

        while time.time() - start_time < timeout:
            job_status = emr_client.get_job_run(
                applicationId=emr_application_id, jobRunId=job_run_id
            )
            state = job_status['jobRun']['state']

            if state in ['SUCCESS', 'FAILED', 'CANCELLED']:
                tool_result = {
                    'status': 'success' if state == 'SUCCESS' else 'error',
                    'execution_platform': 'emr',
                    's3_output_path': s3_output_path,
                    'job_run_id': job_run_id,
                    'job_state': state,
                    'emr_application_id': emr_application_id,
                }
                update_progress(s3_bucket, session_id, "execute_spark_on_emr", "complete" if state == "SUCCESS" else "error", f"EMR job {state}", region)
                return {'statusCode': 200, 'body': json.dumps(tool_result)}

            time.sleep(10)

        # Timeout
        tool_result = {
            'status': 'timeout',
            'execution_platform': 'emr',
            'job_run_id': job_run_id,
            'message': f'Job exceeded timeout of {emr_timeout_minutes} minutes',
        }
        return {'statusCode': 200, 'body': json.dumps(tool_result)}

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'execution_platform': 'emr',
                'error': str(e),
            }),
        }
