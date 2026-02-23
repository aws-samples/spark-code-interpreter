#!/usr/bin/env python3
"""Cleanup Ray EKS deployment"""

import json
import subprocess
import sys
import yaml

class RayEKSCleanup:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.region = self.config['aws']['region']
        self.profile = self.config['aws'].get('profile', 'default')
        
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
        cluster_name = self.config['eks']['cluster_name']
        
        # Delete Ray cluster
        print("\n=== Deleting Ray Cluster ===")
        self.run_cmd(['kubectl', 'delete', 'raycluster', '--all', '-n', 
                     self.config['ray']['namespace']])
        
        # Delete namespaces
        print("\n=== Deleting Namespaces ===")
        self.run_cmd(['kubectl', 'delete', 'namespace', self.config['ray']['namespace']])
        self.run_cmd(['kubectl', 'delete', 'namespace', self.config['kuberay']['namespace']])
        
        # Delete EKS cluster
        print("\n=== Deleting EKS Cluster ===")
        self.aws_cmd('eks', 'delete-cluster', '--name', cluster_name)
        
        print("Waiting for cluster deletion...")
        import time
        time.sleep(30)
        
        # Delete VPC if created
        if not self.config['network']['use_existing']:
            print("\n=== Deleting VPC Resources ===")
            try:
                vpc_result = subprocess.run(
                    ['aws', '--region', self.region, '--profile', self.profile,
                     'ec2', 'describe-vpcs', '--filters', 
                     f"Name=tag:Name,Values={cluster_name}-vpc"],
                    capture_output=True, text=True
                )
                if vpc_result.returncode == 0:
                    vpcs = json.loads(vpc_result.stdout).get('Vpcs', [])
                    if vpcs:
                        vpc_id = vpcs[0]['VpcId']
                        print(f"Deleting VPC: {vpc_id}")
                        
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
        
        print("\n" + "="*50)
        print("Cleanup completed!")
        print("="*50)

if __name__ == '__main__':
    cleanup = RayEKSCleanup()
    cleanup.cleanup()
