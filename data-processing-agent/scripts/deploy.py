#!/usr/bin/env python3
"""Deploy Ray cluster on EKS with Auto Mode"""

import json
import subprocess
import sys
import time
import yaml
from pathlib import Path

class RayEKSDeployer:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.region = self.config['aws']['region']
        self.profile = self.config['aws'].get('profile', 'default')
        
    def run_cmd(self, cmd, check=True):
        """Execute shell command"""
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"Error: {result.stderr}")
            sys.exit(1)
        return result.stdout.strip()
    
    def aws_cmd(self, *args):
        """Execute AWS CLI command"""
        cmd = ['aws', '--region', self.region, '--profile', self.profile] + list(args)
        return self.run_cmd(cmd)
    
    def kubectl_cmd(self, *args):
        """Execute kubectl command"""
        cmd = ['kubectl'] + list(args)
        return self.run_cmd(cmd)
    
    def create_vpc(self):
        """Create VPC and subnets"""
        print("\n=== Creating VPC ===")
        vpc_cidr = self.config['network']['vpc_cidr']
        
        vpc_id = json.loads(self.aws_cmd('ec2', 'create-vpc', '--cidr-block', vpc_cidr))['Vpc']['VpcId']
        print(f"Created VPC: {vpc_id}")
        
        self.aws_cmd('ec2', 'create-tags', '--resources', vpc_id, 
                     '--tags', f"Key=Name,Value={self.config['eks']['cluster_name']}-vpc")
        
        # Enable DNS
        self.aws_cmd('ec2', 'modify-vpc-attribute', '--vpc-id', vpc_id, '--enable-dns-hostnames')
        self.aws_cmd('ec2', 'modify-vpc-attribute', '--vpc-id', vpc_id, '--enable-dns-support')
        
        # Create Internet Gateway
        igw_id = json.loads(self.aws_cmd('ec2', 'create-internet-gateway'))['InternetGateway']['InternetGatewayId']
        self.aws_cmd('ec2', 'attach-internet-gateway', '--vpc-id', vpc_id, '--internet-gateway-id', igw_id)
        
        # Get AZs
        azs = json.loads(self.aws_cmd('ec2', 'describe-availability-zones', '--filters', 
                                      'Name=state,Values=available'))['AvailabilityZones']
        az_count = self.config['network']['availability_zones']
        
        subnet_ids = []
        for i in range(az_count):
            cidr = f"10.0.{i}.0/24"
            subnet = json.loads(self.aws_cmd('ec2', 'create-subnet', '--vpc-id', vpc_id, 
                                             '--cidr-block', cidr, '--availability-zone', azs[i]['ZoneName']))
            subnet_id = subnet['Subnet']['SubnetId']
            subnet_ids.append(subnet_id)
            self.aws_cmd('ec2', 'modify-subnet-attribute', '--subnet-id', subnet_id, 
                        '--map-public-ip-on-launch')
            print(f"Created subnet: {subnet_id}")
        
        # Create route table
        rt_id = json.loads(self.aws_cmd('ec2', 'describe-route-tables', '--filters', 
                                        f'Name=vpc-id,Values={vpc_id}'))['RouteTables'][0]['RouteTableId']
        self.aws_cmd('ec2', 'create-route', '--route-table-id', rt_id, 
                    '--destination-cidr-block', '0.0.0.0/0', '--gateway-id', igw_id)
        
        return vpc_id, subnet_ids
    
    def create_eks_cluster(self):
        """Create EKS cluster with Auto Mode"""
        print("\n=== Creating EKS Cluster ===")
        
        cluster_name = self.config['eks']['cluster_name']
        k8s_version = self.config['eks']['kubernetes_version']
        
        # Get or create network resources
        if self.config['network']['use_existing']:
            vpc_id = self.config['network']['vpc_id']
            subnet_ids = self.config['network']['subnet_ids']
            print(f"Using existing VPC: {vpc_id}")
        else:
            vpc_id, subnet_ids = self.create_vpc()
        
        # Create cluster
        cmd_args = [
            'eks', 'create-cluster',
            '--name', cluster_name,
            '--kubernetes-version', k8s_version,
            '--compute-config', 'enabled=true,nodeRoleArn=auto',
            '--kubernetes-network-config', f"ipFamily=ipv4",
            '--resources-vpc-config', f"subnetIds={','.join(subnet_ids)}"
        ]
        
        self.aws_cmd(*cmd_args)
        
        print("Waiting for cluster to be active...")
        while True:
            status = json.loads(self.aws_cmd('eks', 'describe-cluster', '--name', cluster_name))
            if status['cluster']['status'] == 'ACTIVE':
                break
            print(".", end="", flush=True)
            time.sleep(30)
        print("\nCluster is active!")
        
        # Update kubeconfig
        self.aws_cmd('eks', 'update-kubeconfig', '--name', cluster_name)
        
        return cluster_name
    
    def install_kuberay_operator(self):
        """Install KubeRay operator"""
        print("\n=== Installing KubeRay Operator ===")
        
        namespace = self.config['kuberay']['namespace']
        version = self.config['kuberay']['version']
        
        # Create namespace
        self.run_cmd(['kubectl', 'create', 'namespace', namespace], check=False)
        
        # Install operator using Helm
        self.run_cmd(['helm', 'repo', 'add', 'kuberay', 
                     'https://ray-project.github.io/kuberay-helm/'], check=False)
        self.run_cmd(['helm', 'repo', 'update'])
        
        self.run_cmd(['helm', 'install', 'kuberay-operator', 'kuberay/kuberay-operator',
                     '--namespace', namespace, '--version', version,
                     '--set', 'image.tag=v' + version])
        
        print("Waiting for operator to be ready...")
        time.sleep(10)
        self.kubectl_cmd('wait', '--for=condition=available', '--timeout=300s',
                        'deployment/kuberay-operator', '-n', namespace)
    
    def deploy_ray_cluster(self):
        """Deploy Ray cluster"""
        print("\n=== Deploying Ray Cluster ===")
        
        # Create Ray namespace
        ray_ns = self.config['ray']['namespace']
        self.run_cmd(['kubectl', 'create', 'namespace', ray_ns], check=False)
        
        # Generate Ray cluster manifest
        manifest_path = Path('ray-cluster.yaml')
        self.generate_ray_manifest(manifest_path)
        
        # Apply manifest
        self.kubectl_cmd('apply', '-f', str(manifest_path))
        
        print("Waiting for Ray cluster to be ready...")
        time.sleep(15)
        
        print("\nRay cluster deployed successfully!")
    
    def generate_ray_manifest(self, output_path):
        """Generate Ray cluster Kubernetes manifest"""
        ray_config = self.config['ray']
        
        manifest = {
            'apiVersion': 'ray.io/v1',
            'kind': 'RayCluster',
            'metadata': {
                'name': ray_config['cluster_name'],
                'namespace': ray_config['namespace']
            },
            'spec': {
                'rayVersion': ray_config['ray_version'],
                'enableInTreeAutoscaling': ray_config['autoscaling']['enabled'],
                'headGroupSpec': {
                    'rayStartParams': {
                        'dashboard-host': '0.0.0.0'
                    },
                    'template': {
                        'spec': {
                            'containers': [{
                                'name': 'ray-head',
                                'image': f"rayproject/ray:{ray_config['ray_version']}",
                                'resources': {
                                    'limits': {
                                        'cpu': ray_config['head']['cpu'],
                                        'memory': ray_config['head']['memory']
                                    },
                                    'requests': {
                                        'cpu': ray_config['head']['cpu'],
                                        'memory': ray_config['head']['memory']
                                    }
                                },
                                'ports': [
                                    {'containerPort': 6379, 'name': 'gcs-server'},
                                    {'containerPort': 8265, 'name': 'dashboard'},
                                    {'containerPort': 10001, 'name': 'client'}
                                ]
                            }]
                        }
                    }
                },
                'workerGroupSpecs': [{
                    'groupName': 'worker-group',
                    'replicas': ray_config['worker']['replicas_default'],
                    'minReplicas': ray_config['worker']['min_replicas'],
                    'maxReplicas': ray_config['worker']['max_replicas'],
                    'rayStartParams': {},
                    'template': {
                        'spec': {
                            'containers': [{
                                'name': 'ray-worker',
                                'image': f"rayproject/ray:{ray_config['ray_version']}",
                                'resources': {
                                    'limits': {
                                        'cpu': ray_config['worker']['cpu'],
                                        'memory': ray_config['worker']['memory']
                                    },
                                    'requests': {
                                        'cpu': ray_config['worker']['cpu'],
                                        'memory': ray_config['worker']['memory']
                                    }
                                }
                            }]
                        }
                    }
                }]
            }
        }
        
        if ray_config['autoscaling']['enabled']:
            manifest['spec']['autoscalerOptions'] = {
                'idleTimeoutSeconds': ray_config['autoscaling']['idle_timeout_seconds']
            }
        
        with open(output_path, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False)
        
        print(f"Generated Ray cluster manifest: {output_path}")
    
    def deploy(self):
        """Main deployment workflow"""
        print("Starting Ray on EKS deployment...")
        
        try:
            cluster_name = self.create_eks_cluster()
            self.install_kuberay_operator()
            self.deploy_ray_cluster()
            
            print("\n" + "="*50)
            print("Deployment completed successfully!")
            print("="*50)
            print(f"\nCluster: {cluster_name}")
            print(f"Region: {self.region}")
            print("\nTo access Ray dashboard:")
            print(f"  kubectl port-forward -n {self.config['ray']['namespace']} " +
                  f"service/{self.config['ray']['cluster_name']}-head-svc 8265:8265")
            print("\nThen open: http://localhost:8265")
            
        except Exception as e:
            print(f"\nDeployment failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    deployer = RayEKSDeployer()
    deployer.deploy()
