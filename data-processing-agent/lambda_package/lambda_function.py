import json
import requests
import time

def lambda_handler(event, context):
    """Validate Ray code by executing on remote Ray cluster"""
    
    print(f"Lambda invoked with event: {json.dumps(event)}")
    
    try:
        # Handle both direct invocation and MCP Gateway formats
        if 'arguments' in event:
            # MCP Gateway format
            args = event['arguments']
            code = args.get('code', '')
            ray_cluster_ip = args.get('ray_cluster_ip', '172.31.4.12')
        else:
            # Direct invocation format
            code = event.get('code', '')
            ray_cluster_ip = event.get('ray_cluster_ip', '172.31.4.12')
        
        print(f"Code length: {len(code)}")
        print(f"Ray cluster IP: {ray_cluster_ip}")
        
        if not code:
            print("No code provided")
            return {
                'success': False,
                'error': 'No code provided'
            }
        
        # Ray cluster endpoints
        ray_dashboard_url = f"http://{ray_cluster_ip}:8265"
        ray_jobs_api = f"{ray_dashboard_url}/api/jobs/"
        
        print(f"Testing connectivity to {ray_dashboard_url}")
        
        # Test connectivity
        try:
            response = requests.get(f"{ray_dashboard_url}/api/cluster_status", timeout=10)
            print(f"Cluster status response: {response.status_code}")
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Cannot connect to Ray cluster at {ray_cluster_ip}:8265'
                }
        except Exception as e:
            print(f"Connectivity error: {e}")
            return {
                'success': False,
                'error': f'Cannot connect to Ray cluster at {ray_cluster_ip}:8265. Network connectivity issue.'
            }
        
        # Submit Ray job
        job_spec = {
            "entrypoint": f"python -c \"{code.replace(chr(34), chr(92)+chr(34))}\"",
            "runtime_env": {},
            "job_id": None,
            "metadata": {"job_submission_id": f"validation_{int(time.time())}"}
        }
        
        print(f"Submitting job to {ray_jobs_api}")
        
        try:
            submit_response = requests.post(ray_jobs_api, json=job_spec, timeout=30)
            print(f"Job submission response: {submit_response.status_code}")
            
            if submit_response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Job submission failed: {submit_response.status_code} - {submit_response.text}'
                }
            
            job_data = submit_response.json()
            job_id = job_data.get('job_id')
            print(f"Job submitted with ID: {job_id}")
            
            # Poll for job completion
            max_polls = 150  # 5 minutes total
            poll_interval = 2
            
            for i in range(max_polls):
                time.sleep(poll_interval)
                
                status_response = requests.get(f"{ray_jobs_api}{job_id}", timeout=10)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status')
                    print(f"Job status check {i+1}: {status}")
                    
                    if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                        break
                else:
                    print(f"Status check failed: {status_response.status_code}")
            
            # Handle final status
            if status == 'SUCCEEDED':
                print(f"Job succeeded! Getting job logs...")
                
                # Get job logs
                try:
                    logs_response = requests.get(f"{ray_jobs_api}{job_id}/logs", timeout=10)
                    output = ""
                    
                    if logs_response.status_code == 200:
                        logs_data = logs_response.json()
                        print(f"Logs data type: {type(logs_data)}")
                        
                        # Ray returns logs in a "logs" field as a string
                        if isinstance(logs_data, dict) and 'logs' in logs_data:
                            output = logs_data['logs']
                        elif isinstance(logs_data, str):
                            output = logs_data
                        else:
                            output = str(logs_data)
                    
                    if not output.strip():
                        output = f"Job completed successfully (Job ID: {job_id})"
                        
                except Exception as log_error:
                    print(f"Failed to get logs: {log_error}")
                    output = f"Job completed successfully (Job ID: {job_id})"
                
                return {
                    'success': True,
                    'job_id': job_id,
                    'status': status,
                    'output': output.strip()
                }
            elif status in ['FAILED', 'STOPPED']:
                print(f"Job failed with status: {status}")
                return {
                    'success': False,
                    'job_id': job_id,
                    'status': status,
                    'error': f'Ray job {status.lower()}'
                }
            else:
                print(f"Job timed out with status: {status}")
                return {
                    'success': False,
                    'job_id': job_id,
                    'status': status,
                    'error': 'Job execution timed out'
                }
                
        except Exception as e:
            print(f"Job execution error: {e}")
            return {
                'success': False,
                'error': f'Job execution failed: {str(e)}'
            }
            
    except Exception as e:
        print(f"Lambda error: {e}")
        return {
            'success': False,
            'error': f'Lambda execution failed: {str(e)}'
        }
