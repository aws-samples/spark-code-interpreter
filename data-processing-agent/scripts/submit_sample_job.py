#!/usr/bin/env python3
"""Submit sample Ray code to ECS cluster"""

import requests
import base64
import time
import os
import re

RAY_HEAD_IP = os.getenv('RAY_HEAD_IP', '13.220.45.214')
RAY_JOBS_API = f"http://{RAY_HEAD_IP}:8265/api/jobs/"

# Sample Ray code
sample_code = """
import ray

# Create dataset with 100 rows
ds = ray.data.range(100)

# Transform: square each value
ds_squared = ds.map(lambda x: {"id": x["id"], "square": x["id"] ** 2})

# Filter: only values > 50
ds_filtered = ds_squared.filter(lambda x: x["square"] > 50)

# Get results
results = ds_filtered.take(10)

print("=" * 60)
print("SAMPLE RAY JOB RESULTS")
print("=" * 60)
print(f"Total rows after filter: {ds_filtered.count()}")
print(f"\\nFirst 10 results:")
for i, row in enumerate(results, 1):
    print(f"  {i}. ID: {row['id']}, Square: {row['square']}")
print("=" * 60)
"""

def submit_job():
    """Submit job to Ray cluster"""
    
    # Wrap with ray.init
    script = f"""import ray
ray.init(address='auto')
{sample_code}
"""
    
    # Encode
    encoded = base64.b64encode(script.encode()).decode()
    
    # Submit
    print("Submitting job to Ray cluster...")
    print(f"Ray API: {RAY_JOBS_API}")
    
    job_data = {
        "entrypoint": f"python -c \"import base64; exec(base64.b64decode('{encoded}').decode())\""
    }
    
    response = requests.post(RAY_JOBS_API, json=job_data, timeout=5)
    response.raise_for_status()
    
    job_id = response.json()['job_id']
    print(f"✅ Job submitted: {job_id}")
    print(f"Dashboard: http://{RAY_HEAD_IP}:8265")
    
    # Poll for completion
    print("\nWaiting for job to complete...")
    while True:
        status_response = requests.get(f"{RAY_JOBS_API}{job_id}")
        status_data = status_response.json()
        status = status_data['status']
        
        print(f"  Status: {status}", end='\r')
        
        if status == 'SUCCEEDED':
            print("\n✅ Job completed successfully!")
            
            # Get logs
            logs_response = requests.get(f"{RAY_JOBS_API}{job_id}/logs")
            logs = logs_response.json().get('logs', '')
            
            # Filter to show only user output
            skip_patterns = re.compile(
                r'INFO |WARNING |DEBUG |ERROR |'
                r'Running|ReadRange|Map\(|Filter\(|AggregateNumRows|'
                r'Tasks:|Resources:|Dataset execution|'
                r'row \[|row/s\]|\x1b\[|Active & requested|'
                r'UserWarning|warnings\.warn'
            )
            
            output_lines = []
            for line in logs.split('\n'):
                if skip_patterns.search(line):
                    continue
                if line.strip() and not line.strip().startswith('✔️'):
                    output_lines.append(line)
            
            print("\n" + "=" * 60)
            print("JOB OUTPUT")
            print("=" * 60)
            print('\n'.join(output_lines))
            break
            
        elif status == 'FAILED':
            print("\n❌ Job failed!")
            logs_response = requests.get(f"{RAY_JOBS_API}{job_id}/logs")
            logs = logs_response.json().get('logs', '')
            print("\nError logs:")
            print(logs[-1000:])
            break
        
        time.sleep(2)

if __name__ == '__main__':
    submit_job()
