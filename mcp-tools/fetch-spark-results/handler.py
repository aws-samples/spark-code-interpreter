"""MCP Tool: fetch_spark_results
Fetch Spark execution results from S3 output path (CSV or Parquet).
"""

import json
import boto3
from datetime import datetime, timezone, timedelta
from io import StringIO, BytesIO


def lambda_handler(event, context):
    try:
        import pandas as pd
    except ImportError:
        return {
            'statusCode': 500,
            'body': json.dumps({'status': 'error', 'error': 'pandas not available'}),
        }

    s3_output_path = event['s3_output_path']
    s3_bucket = event['s3_bucket']
    max_rows = event.get('max_rows', 100)
    presigned_url_expiry_hours = event.get('presigned_url_expiry_hours', 24)
    region = event.get('region', 'us-east-1')

    try:
        s3_client = boto3.client('s3', region_name=region)
        bucket = s3_output_path.replace('s3://', '').split('/')[0]
        prefix = '/'.join(s3_output_path.replace('s3://', '').split('/')[1:])

        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)

        # Check for CSV files
        csv_files = [
            (obj['Key'], obj['LastModified'])
            for obj in response.get('Contents', [])
            if obj['Key'].endswith('.csv')
            and not obj['Key'].endswith('_SUCCESS')
            and obj['LastModified'] > cutoff_time
        ]

        # Check for part files
        part_files = [
            (obj['Key'], obj['LastModified'])
            for obj in response.get('Contents', [])
            if 'part-' in obj['Key']
            and obj['Key'].endswith('.csv')
            and obj['LastModified'] > cutoff_time
        ]

        all_csv_files = csv_files + part_files

        # Fallback to Parquet
        parquet_files = [
            (obj['Key'], obj['LastModified'])
            for obj in response.get('Contents', [])
            if obj['Key'].endswith('.parquet')
            and not obj['Key'].endswith('_SUCCESS')
            and obj['LastModified'] > cutoff_time
        ]

        if all_csv_files:
            regular_csv = [f for f in all_csv_files if 'part-' not in f[0]]
            files_to_process = regular_csv if regular_csv else all_csv_files
            files_to_process.sort(key=lambda x: x[1], reverse=True)
            most_recent_file = files_to_process[0][0]

            obj = s3_client.get_object(Bucket=bucket, Key=most_recent_file)
            csv_content = obj['Body'].read().decode('utf-8')

            lines = csv_content.strip().split('\n')
            if len(lines) > 1:
                first_row = lines[0].split(',')
                has_headers = any(
                    not val.strip().replace('.', '').replace('-', '').isdigit()
                    for val in first_row
                    if val.strip()
                )
            else:
                has_headers = False

            df = (
                pd.read_csv(StringIO(csv_content))
                if has_headers
                else pd.read_csv(StringIO(csv_content), header=None)
            )
            file_format = 'csv'

        elif parquet_files:
            parquet_files.sort(key=lambda x: x[1], reverse=True)
            most_recent_file = parquet_files[0][0]

            obj = s3_client.get_object(Bucket=bucket, Key=most_recent_file)
            parquet_content = obj['Body'].read()
            df = pd.read_parquet(BytesIO(parquet_content))
            file_format = 'parquet'

        else:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'data': [],
                    'row_count': 0,
                    'message': 'No recent CSV or Parquet files found in output path',
                }),
            }

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': most_recent_file},
            ExpiresIn=presigned_url_expiry_hours * 3600,
        )

        result = {
            'status': 'success',
            'data': df.head(max_rows).to_dict('records'),
            'row_count': len(df),
            'preview_rows': max_rows,
            'total_files': len(all_csv_files) + len(parquet_files),
            'file_format': file_format,
            'presigned_url': presigned_url,
            's3_path': f"s3://{bucket}/{most_recent_file}",
        }

        return {'statusCode': 200, 'body': json.dumps(result, default=str)}

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'data': [],
                'row_count': 0,
            }),
        }
