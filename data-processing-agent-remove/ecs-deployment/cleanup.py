#!/usr/bin/env python3
"""Cleanup Ray ECS deployment"""

import json
import subprocess
import sys
import time
import yaml

class RayECSCleanup:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.region = self.config['aws']['region']
        self.profile = self.config['aws'].get('profile', 'default')
        self.cluster_name = self.config['ecs']['cluster_name']
        
    def run_cmd(self, cmd, check=False):
        """Execute shell command"""
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    
    def aws_cmd(self, *args):
        """Execute AWS CLI command"""
        cmd = ['aws', '--region', self.region, '--profile', self.profile] + list(args)
        return self.run_cmd(cmd)
    
    def cleanup(self):
        """Remove all resources"""
        print("Starting cleanup...")
        
        # Delete ECS services
        print("\n=== Deleting ECS Services ===")
        try:
            services = json.loads(subprocess.run(
                ['aws', '--region', self.region, '--profile', self.profile,
                 'ecs', 'list-services', '--cluster', self.cluster_name],
                capture_output=True, text=True
            ).stdout)
            
            for service_arn in services.get('serviceArns', []):
                service_name = service_arn.split('/')[-1]
                print(f"Deleting service: {service_name}")
                self.aws_cmd('ecs', 'update-service', '--cluster', self.cluster_name,
                           '--service', service_name, '--desired-count', '0')
                self.aws_cmd('ecs', 'delete-service', '--cluster', self.cluster_name,
                           '--service', service_name, '--force')
        except Exception as e:
            print(f"Error deleting services: {e}")
        
        time.sleep(10)
        
        # Delete ECS cluster
        print("\n=== Deleting ECS Cluster ===")
        self.aws_cmd('ecs', 'delete-cluster', '--cluster', self.cluster_name)
        
        # Deregister task definitions
        print("\n=== Deregistering Task Definitions ===")
        for family in [f"{self.cluster_name}-head", f"{self.cluster_name}-worker"]:
            try:
                task_defs = json.loads(subprocess.run(
                    ['aws', '--region', self.region, '--profile', self.profile,
                     'ecs', 'list-task-definitions', '--family-prefix', family],
                    capture_output=True, text=True
                ).stdout)
                
                for task_def_arn in task_defs.get('taskDefinitionArns', []):
                    self.aws_cmd('ecs', 'deregister-task-definition', '--task-definition', task_def_arn)
            except Exception as e:
                print(f"Error deregistering task definitions: {e}")
        
        # Delete service discovery
        print("\n=== Deleting Service Discovery ===")
        try:
            namespace = self.config['service_discovery']['namespace']
            namespaces = json.loads(subprocess.run(
                ['aws', '--region', self.region, '--profile', self.profile,
                 'servicediscovery', 'list-namespaces'],
                capture_output=True, text=True
            ).stdout)
            
            for ns in namespaces.get('Namespaces', []):
                if ns['Name'] == namespace:
                    ns_id = ns['Id']
                    
                    # Delete services in namespace
                    services = json.loads(subprocess.run(
                        ['aws', '--region', self.region, '--profile', self.profile,
                         'servicediscovery', 'list-services'],
                        capture_output=True, text=True
                    ).stdout)
                    
                    for svc in services.get('Services', []):
                        self.aws_cmd('servicediscovery', 'delete-service', '--id', svc['Id'])
                    
                    time.sleep(5)
                    self.aws_cmd('servicediscovery', 'delete-namespace', '--id', ns_id)
        except Exception as e:
            print(f"Error deleting service discovery: {e}")
        
        # Delete security group
        print("\n=== Deleting Security Group ===")
        try:
            sgs = json.loads(subprocess.run(
                ['aws', '--region', self.region, '--profile', self.profile,
                 'ec2', 'describe-security-groups', '--filters',
                 f'Name=group-name,Values={self.cluster_name}-sg'],
                capture_output=True, text=True
            ).stdout)
            
            for sg in sgs.get('SecurityGroups', []):
                time.sleep(10)  # Wait for ENIs to be released
                self.aws_cmd('ec2', 'delete-security-group', '--group-id', sg['GroupId'])
        except Exception as e:
            print(f"Error deleting security group: {e}")
        
        # Delete IAM roles
        print("\n=== Deleting IAM Roles ===")
        for role_name in [f'{self.cluster_name}-exec-role', f'{self.cluster_name}-task-role']:
            try:
                # Detach policies
                policies = json.loads(subprocess.run(
                    ['aws', '--region', self.region, '--profile', self.profile,
                     'iam', 'list-attached-role-policies', '--role-name', role_name],
                    capture_output=True, text=True
                ).stdout)
                
                for policy in policies.get('AttachedPolicies', []):
                    self.aws_cmd('iam', 'detach-role-policy', '--role-name', role_name,
                               '--policy-arn', policy['PolicyArn'])
                
                self.aws_cmd('iam', 'delete-role', '--role-name', role_name)
            except Exception as e:
                print(f"Error deleting role {role_name}: {e}")
        
        # Delete VPC if created
        if not self.config['network']['use_existing']:
            print("\n=== Deleting VPC Resources ===")
            try:
                vpc_result = subprocess.run(
                    ['aws', '--region', self.region, '--profile', self.profile,
                     'ec2', 'describe-vpcs', '--filters',
                     f"Name=tag:Name,Values={self.cluster_name}-vpc"],
                    capture_output=True, text=True
                )
                
                if vpc_result.returncode == 0:
                    vpcs = json.loads(vpc_result.stdout).get('Vpcs', [])
                    if vpcs:
                        vpc_id = vpcs[0]['VpcId']
                        print(f"Deleting VPC: {vpc_id}")
                        
                        time.sleep(30)  # Wait for ENIs to be released
                        
                        # Delete subnets
                        subnets = json.loads(subprocess.run(
                            ['aws', '--region', self.region, '--profile', self.profile,
                             'ec2', 'describe-subnets', '--filters', f'Name=vpc-id,Values={vpc_id}'],
                            capture_output=True, text=True
                        ).stdout)['Subnets']
                        
                        for subnet in subnets:
                            self.aws_cmd('ec2', 'delete-subnet', '--subnet-id', subnet['SubnetId'])
                        
                        # Delete IGW
                        igws = json.loads(subprocess.run(
                            ['aws', '--region', self.region, '--profile', self.profile,
                             'ec2', 'describe-internet-gateways', '--filters',
                             f'Name=attachment.vpc-id,Values={vpc_id}'],
                            capture_output=True, text=True
                        ).stdout)['InternetGateways']
                        
                        for igw in igws:
                            igw_id = igw['InternetGatewayId']
                            self.aws_cmd('ec2', 'detach-internet-gateway', '--vpc-id', vpc_id,
                                       '--internet-gateway-id', igw_id)
                            self.aws_cmd('ec2', 'delete-internet-gateway', '--internet-gateway-id', igw_id)
                        
                        # Delete VPC
                        time.sleep(10)
                        self.aws_cmd('ec2', 'delete-vpc', '--vpc-id', vpc_id)
            except Exception as e:
                print(f"Error cleaning up VPC: {e}")
        
        # Delete log group
        print("\n=== Deleting Log Group ===")
        log_group = f'/ecs/{self.cluster_name}'
        self.aws_cmd('logs', 'delete-log-group', '--log-group-name', log_group)
        
        print("\n" + "="*50)
        print("Cleanup completed!")
        print("="*50)

if __name__ == '__main__':
    cleanup = RayECSCleanup()
    cleanup.cleanup()
