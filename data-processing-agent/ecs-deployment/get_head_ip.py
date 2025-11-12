#!/usr/bin/env python3
"""Get the public IP of the Ray head node"""

import json
import subprocess
import yaml

def get_head_ip():
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    region = config['aws']['region']
    profile = config['aws'].get('profile', 'default')
    cluster_name = config['ecs']['cluster_name']
    service_name = f"{cluster_name}-head"
    
    # List tasks
    result = subprocess.run(
        ['aws', '--region', region, '--profile', profile,
         'ecs', 'list-tasks', '--cluster', cluster_name,
         '--service-name', service_name],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error listing tasks: {result.stderr}")
        return None
    
    tasks = json.loads(result.stdout)
    if not tasks.get('taskArns'):
        print("No running tasks found")
        return None
    
    task_arn = tasks['taskArns'][0]
    
    # Describe task
    result = subprocess.run(
        ['aws', '--region', region, '--profile', profile,
         'ecs', 'describe-tasks', '--cluster', cluster_name,
         '--tasks', task_arn],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error describing task: {result.stderr}")
        return None
    
    task_details = json.loads(result.stdout)
    task = task_details['tasks'][0]
    
    # Get ENI ID
    for attachment in task.get('attachments', []):
        if attachment['type'] == 'ElasticNetworkInterface':
            for detail in attachment['details']:
                if detail['name'] == 'networkInterfaceId':
                    eni_id = detail['value']
                    
                    # Get public IP from ENI
                    result = subprocess.run(
                        ['aws', '--region', region, '--profile', profile,
                         'ec2', 'describe-network-interfaces',
                         '--network-interface-ids', eni_id],
                        capture_output=True, text=True
                    )
                    
                    if result.returncode == 0:
                        eni_details = json.loads(result.stdout)
                        public_ip = eni_details['NetworkInterfaces'][0].get('Association', {}).get('PublicIp')
                        return public_ip
    
    return None

if __name__ == '__main__':
    ip = get_head_ip()
    if ip:
        print(f"\nRay Head Node Public IP: {ip}")
        print(f"\nRay Dashboard: http://{ip}:8265")
        print(f"Ray Client: ray://{ip}:10001")
        print(f"\nTo connect from Python:")
        print(f'  ray.init("ray://{ip}:10001")')
    else:
        print("Could not find head node IP")
