import json
import traceback
import subprocess
import base64
import os
import boto3
import sys
import re
import tempfile
import logging

class CodeExecutionError(Exception):
    pass

def local_code_executy(code_string, spark_configs):   
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code_string)

    output_file_path = '/tmp/output.json'
    log_file_path = '/tmp/spark_log.txt'

    spark_submit_args = [
        "spark-submit",
        "--conf", "spark.driver.extraJavaOptions=-Dlog4j.configuration=file:/opt/spark/conf/log4j.properties",
        "--conf", "spark.executor.extraJavaOptions=-Dlog4j.configuration=file:/opt/spark/conf/log4j.properties",
    ]
    if spark_configs:
        for key, value in spark_configs.items():
            spark_submit_args.extend(["--conf", f"{key}={value}"])    
    spark_submit_args.append(temp_file_path)

    try:
        print("Starting execution")
        # Execute the temporary file and capture both stdout and stderr
        result = subprocess.run(
           spark_submit_args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        # Write logs to file
        with open(log_file_path, 'w') as log_file:
            log_file.write(result.stdout)
            log_file.write(result.stderr)

        # If execution was successful, read the output
        if os.path.exists(output_file_path):
            with open(output_file_path, 'r') as f:
                output = json.load(f)
            return output
        else:
            raise CodeExecutionError("Output file not found. Execution may have failed without producing output.")

    except subprocess.CalledProcessError as e:
        error_message = parse_error(e.stdout, e.stderr, code_string, log_file_path)
        raise CodeExecutionError(error_message)

    finally:
        # Clean up temporary files
        print("Execution Ended")
        for file_path in [temp_file_path, output_file_path]:
            if os.path.exists(file_path):
                os.remove(file_path)

def parse_error(stdout, stderr, code_string, log_file_path):
    error_message = "Execution Error:\n"

    # Add stdout if it exists
    if stdout:
        error_message += f"Standard Output:\n{stdout}\n\n"

    # Add stderr if it exists
    if stderr:
        error_message += f"Standard Error:\n{stderr}\n\n"

    # Look for Python tracebacks in stderr
    python_error_pattern = r'Traceback \(most recent call last\):(.*?)(?:\n\n|\Z)'
    match = re.search(python_error_pattern, stderr, re.DOTALL)

    if match:
        traceback = match.group(1).strip()
        error_message += f"Python Traceback:\n{traceback}\n\n"

        # Extract line number and error message
        line_match = re.search(r'File.*?line (\d+)', traceback)
        error_type_match = re.search(r'(\w+Error:.*?)(?:\n|$)', traceback)

        if line_match and error_type_match:
            line_no = int(line_match.group(1))
            error_type = error_type_match.group(1)

            # Provide context around the error
            code_lines = code_string.split('\n')
            context_lines = 2
            start = max(0, line_no - 1 - context_lines)
            end = min(len(code_lines), line_no + context_lines)

            context = "\n".join([f"{'-> ' if i == line_no else '   '}{i}: {line}" 
                                 for i, line in enumerate(code_lines[start:end], start=start+1)])

            error_message += f"Error on line {line_no}:\n{context}\n\nError Type: {error_type}\n\n"

    # Add contents of log file if it exists
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as log_file:
            log_contents = log_file.read()
            error_message += f"Log File Contents:\n{log_contents}\n\n"

    return error_message
    
def execute_function_string(input_code, trial, bucket, key_prefix, spark_config):
    """
    Execute a given Python code string, potentially modifying dataset paths to use S3. 
    If it's the first trial (trial < 1) and the S3 bucket/prefix are not already in the code:
       - Replaces local dataset references with S3 URIs.

    Parameters:
    input_code (dict): A dictionary containing the following keys:
        - 'code' (str): The Python code to be executed.
        - 'dataset_name' (str or list, optional): Name(s) of the dataset(s) used in the code.
    trial (int): A counter for execution attempts, used to determine if S3 paths should be injected.
    bucket (str): The name of the S3 bucket where datasets are stored.
    key_prefix (str): The S3 key prefix (folder path) where datasets are located within the bucket.

    Returns:
    The result of executing the code using the local_code_executy function.

    """
    code_string = input_code['code']
    dataset_names = input_code.get('dataset_name', [])
    if isinstance(dataset_names, str):
        dataset_names = [d.strip() for d in dataset_names.strip('[]').split(',')]
  
    # Add cluster configuration to spark_config
    return local_code_executy(code_string, spark_config)


def put_obj_in_s3_bucket_(docs, bucket, key_prefix):
    """Uploads a file to an S3 bucket and returns the S3 URI of the uploaded object.
    Args:
       docs (str): The local file path of the file to upload to S3.
       bucket (str): S3 bucket name,
       key_prefix (str): S3 key prefix.
   Returns:
       str: The S3 URI of the uploaded object, in the format "s3://{bucket_name}/{file_path}".
    """
    S3 = boto3.client('s3')
    if isinstance(docs,str):
        file_name=os.path.basename(docs)
        file_path=f"{key_prefix}/{docs}"
        S3.upload_file(f"/tmp/{docs}", bucket, file_path)
    else:
        file_name=os.path.basename(docs.name)
        file_path=f"{key_prefix}/{file_name}"
        S3.put_object(Body=docs.read(),Bucket= BUCKET, Key=file_path)           
    return f"s3://{bucket}/{file_path}"



def lambda_handler(event, context):
    try:
        print("Received request to run Spark job")
        input_data = event['body']
        print(input_data)
        iterate = input_data.get('iterate', 0)
        print(iterate)
        bucket=input_data.get('bucket','')
        s3_file_path=input_data.get('file_path','')        
        spark_config = input_data.get('config', '')
        result = execute_function_string(input_data, iterate, bucket, s3_file_path, spark_config)
        image_holder = []
        plotly_holder = []
        
        if isinstance(result, dict):
            for item, value in result.items():
                if "image" in item and value is not None: # upload PNG files to S3
                    if isinstance(value, list):
                        for img in value:
                            image_path_s3 = put_obj_in_s3_bucket_(img, bucket, s3_file_path)
                            image_holder.append(image_path_s3)                            
                    else:                        
                        image_path_s3 = put_obj_in_s3_bucket_(value, bucket, s3_file_path)
                        image_holder.append(image_path_s3)
                if "plotly-files" in item and value is not None: # Upload plotly objects to s3
                    if isinstance(value, list):
                        for img in value:
                            image_path_s3 = put_obj_in_s3_bucket_(img, bucket, s3_file_path)
                            plotly_holder.append(image_path_s3)                            
                    else:                        
                        image_path_s3 = put_obj_in_s3_bucket_(value, bucket, s3_file_path)
                        plotly_holder.append(image_path_s3)
        
        tool_result = {
            "result": result,            
            "image_dict": image_holder,
            "plotly": plotly_holder
        }
        print(tool_result)
        print("Spark job completed successfully")        
        
        return {
            'statusCode': 200,
            'body': json.dumps(tool_result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
