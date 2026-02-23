#!/usr/bin/env python3
"""Deploy Ray cluster on Amazon ECS"""

import json
import subprocess
import sys
import time
import yaml

class RayECSDeployer:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.region = self.config['aws']['region']
        self.profile = self.config['aws'].get('profile', 'default')
        self.cluster_name = self.config['ecs']['cluster_name']
        
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
    
    def create_vpc(self):
        """Create VPC and subnets"""
        print("\n=== Creating VPC ===")
        vpc_cidr = self.config['network']['vpc_cidr']
        
        vpc_id = json.loads(self.aws_cmd('ec2', 'create-vpc', '--cidr-block', vpc_cidr))['Vpc']['VpcId']
        print(f"Created VPC: {vpc_id}")
        
        self.aws_cmd('ec2', 'create-tags', '--resources', vpc_id,
                     '--tags', f"Key=Name,Value={self.cluster_name}-vpc")
        self.aws_cmd('ec2', 'modify-vpc-attribute', '--vpc-id', vpc_id, '--enable-dns-hostnames')
        self.aws_cmd('ec2', 'modify-vpc-attribute', '--vpc-id', vpc_id, '--enable-dns-support')
        
        # Create Internet Gateway
        igw_id = json.loads(self.aws_cmd('ec2', 'create-internet-gateway'))['InternetGateway']['InternetGatewayId']
        self.aws_cmd('ec2', 'attach-internet-gateway', '--vpc-id', vpc_id, '--internet-gateway-id', igw_id)
        
        # Get AZs
        azs = json.loads(self.aws_cmd('ec2', 'describe-availability-zones',
                                      '--filters', 'Name=state,Values=available'))['AvailabilityZones']
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
        rt_id = json.loads(self.aws_cmd('ec2', 'describe-route-tables',
                                        '--filters', f'Name=vpc-id,Values={vpc_id}'))['RouteTables'][0]['RouteTableId']
        self.aws_cmd('ec2', 'create-route', '--route-table-id', rt_id,
                    '--destination-cidr-block', '0.0.0.0/0', '--gateway-id', igw_id)
        
        return vpc_id, subnet_ids
    
    def create_security_group(self, vpc_id):
        """Create security group for Ray cluster"""
        print("\n=== Creating Security Group ===")
        
        sg_id = json.loads(self.aws_cmd('ec2', 'create-security-group',
                                        '--group-name', f'{self.cluster_name}-sg',
                                        '--description', 'Security group for Ray cluster',
                                        '--vpc-id', vpc_id))['GroupId']
        
        # Allow all traffic within security group
        self.aws_cmd('ec2', 'authorize-security-group-ingress',
                    '--group-id', sg_id,
                    '--protocol', 'all',
                    '--source-group', sg_id)
        
        # Allow dashboard access from anywhere (for testing)
        self.aws_cmd('ec2', 'authorize-security-group-ingress',
                    '--group-id', sg_id,
                    '--protocol', 'tcp',
                    '--port', '8265',
                    '--cidr', '0.0.0.0/0')
        
        print(f"Created security group: {sg_id}")
        return sg_id
    
    def create_iam_roles(self):
        """Create IAM roles for ECS tasks"""
        print("\n=== Creating IAM Roles ===")
        
        # Task execution role
        exec_role_name = f'{self.cluster_name}-exec-role'
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }
        
        try:
            exec_role_arn = json.loads(self.aws_cmd('iam', 'create-role',
                                                     '--role-name', exec_role_name,
                                                     '--assume-role-policy-document', json.dumps(trust_policy)))['Role']['Arn']
            
            self.aws_cmd('iam', 'attach-role-policy',
                        '--role-name', exec_role_name,
                        '--policy-arn', 'arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy')
        except:
            exec_role_arn = json.loads(self.aws_cmd('iam', 'get-role',
                                                     '--role-name', exec_role_name))['Role']['Arn']
        
        # Task role
        task_role_name = f'{self.cluster_name}-task-role'
        try:
            task_role_arn = json.loads(self.aws_cmd('iam', 'create-role',
                                                     '--role-name', task_role_name,
                                                     '--assume-role-policy-document', json.dumps(trust_policy)))['Role']['Arn']
        except:
            task_role_arn = json.loads(self.aws_cmd('iam', 'get-role',
                                                     '--role-name', task_role_name))['Role']['Arn']
        
        print(f"Execution role: {exec_role_arn}")
        print(f"Task role: {task_role_arn}")
        
        time.sleep(10)  # Wait for IAM propagation
        return exec_role_arn, task_role_arn
    
    def create_service_discovery(self):
        """Create AWS Cloud Map namespace for service discovery"""
        print("\n=== Creating Service Discovery ===")
        
        namespace = self.config['service_discovery']['namespace']
        
        try:
            ns_id = json.loads(self.aws_cmd('servicediscovery', 'create-private-dns-namespace',
                                            '--name', namespace,
                                            '--vpc', self.vpc_id))['OperationId']
            
            # Wait for namespace creation
            time.sleep(10)
            operation = json.loads(self.aws_cmd('servicediscovery', 'get-operation',
                                                '--operation-id', ns_id))
            namespace_id = operation['Operation']['Targets']['NAMESPACE']
        except:
            namespaces = json.loads(self.aws_cmd('servicediscovery', 'list-namespaces'))
            namespace_id = next(ns['Id'] for ns in namespaces['Namespaces'] if ns['Name'] == namespace)
        
        print(f"Service discovery namespace: {namespace_id}")
        return namespace_id
    
    def create_ecs_cluster(self):
        """Create ECS cluster"""
        print("\n=== Creating ECS Cluster ===")
        
        self.aws_cmd('ecs', 'create-cluster', '--cluster-name', self.cluster_name)
        print(f"Created ECS cluster: {self.cluster_name}")
    
    def create_log_group(self):
        """Create CloudWatch log group"""
        print("\n=== Creating Log Group ===")
        
        log_group = f'/ecs/{self.cluster_name}'
        try:
            self.aws_cmd('logs', 'create-log-group', '--log-group-name', log_group)
        except:
            pass
        print(f"Log group: {log_group}")
        return log_group
    
    def register_head_task_definition(self, exec_role_arn, task_role_arn, log_group):
        """Register Ray head node task definition"""
        print("\n=== Registering Head Task Definition ===")
        
        head_config = self.config['ray_head']
        
        task_def = {
            "family": f"{self.cluster_name}-head",
            "networkMode": "awsvpc",
            "requiresCompatibilities": [self.config['ecs']['launch_type']],
            "cpu": str(head_config['cpu']),
            "memory": str(head_config['memory']),
            "executionRoleArn": exec_role_arn,
            "taskRoleArn": task_role_arn,
            "containerDefinitions": [{
                "name": "ray-head",
                "image": f"rayproject/ray:{head_config['ray_version']}",
                "essential": True,
                "entryPoint": ["/bin/bash", "-c"],
                "command": [
                    "pip install torch filelock numpy torchvision awswrangler>=3.0.0 pyarrow>=10.0.0 pyathena>=3.0.0 && "
                    "ray start --head --port=6379 --dashboard-host=0.0.0.0 --block"
                ],
                "portMappings": [
                    {"containerPort": 6379, "protocol": "tcp"},
                    {"containerPort": 8265, "protocol": "tcp"},
                    {"containerPort": 10001, "protocol": "tcp"}
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": log_group,
                        "awslogs-region": self.region,
                        "awslogs-stream-prefix": "ray-head"
                    }
                }
            }]
        }
        
        result = json.loads(self.aws_cmd('ecs', 'register-task-definition',
                                         '--cli-input-json', json.dumps(task_def)))
        print(f"Registered head task definition: {result['taskDefinition']['taskDefinitionArn']}")
        return result['taskDefinition']['taskDefinitionArn']
    
    def register_worker_task_definition(self, exec_role_arn, task_role_arn, log_group, head_address):
        """Register Ray worker task definition"""
        print("\n=== Registering Worker Task Definition ===")
        
        worker_config = self.config['ray_worker']
        
        task_def = {
            "family": f"{self.cluster_name}-worker",
            "networkMode": "awsvpc",
            "requiresCompatibilities": [self.config['ecs']['launch_type']],
            "cpu": str(worker_config['cpu']),
            "memory": str(worker_config['memory']),
            "executionRoleArn": exec_role_arn,
            "taskRoleArn": task_role_arn,
            "containerDefinitions": [{
                "name": "ray-worker",
                "image": f"rayproject/ray:{worker_config['ray_version']}",
                "essential": True,
                "entryPoint": ["/bin/bash", "-c"],
                "command": [
                    "pip install torch filelock numpy torchvision awswrangler>=3.0.0 pyarrow>=10.0.0 pyathena>=3.0.0 && "
                    f"ray start --address={head_address}:6379 --block"
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": log_group,
                        "awslogs-region": self.region,
                        "awslogs-stream-prefix": "ray-worker"
                    }
                }
            }]
        }
        
        result = json.loads(self.aws_cmd('ecs', 'register-task-definition',
                                         '--cli-input-json', json.dumps(task_def)))
        print(f"Registered worker task definition: {result['taskDefinition']['taskDefinitionArn']}")
        return result['taskDefinition']['taskDefinitionArn']
    
    def create_head_service(self, task_def_arn, namespace_id):
        """Create ECS service for Ray head node"""
        print("\n=== Creating Head Service ===")
        
        service_name = f"{self.cluster_name}-head"
        head_config = self.config['ray_head']
        
        service_config = {
            "cluster": self.cluster_name,
            "serviceName": service_name,
            "taskDefinition": task_def_arn,
            "desiredCount": head_config['desired_count'],
            "launchType": self.config['ecs']['launch_type'],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": self.subnet_ids,
                    "securityGroups": [self.security_group_id],
                    "assignPublicIp": "ENABLED"
                }
            },
            "serviceRegistries": [{
                "registryArn": self.create_service_registry(namespace_id, "ray-head")
            }]
        }
        
        result = json.loads(self.aws_cmd('ecs', 'create-service',
                                         '--cli-input-json', json.dumps(service_config)))
        print(f"Created head service: {result['service']['serviceName']}")
        
        # Wait for service to be stable
        print("Waiting for head service to be stable...")
        time.sleep(30)
    
    def create_worker_service(self, task_def_arn):
        """Create ECS service for Ray workers"""
        print("\n=== Creating Worker Service ===")
        
        service_name = f"{self.cluster_name}-worker"
        worker_config = self.config['ray_worker']
        
        service_config = {
            "cluster": self.cluster_name,
            "serviceName": service_name,
            "taskDefinition": task_def_arn,
            "desiredCount": worker_config['desired_count'],
            "launchType": self.config['ecs']['launch_type'],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": self.subnet_ids,
                    "securityGroups": [self.security_group_id],
                    "assignPublicIp": "ENABLED"
                }
            }
        }
        
        result = json.loads(self.aws_cmd('ecs', 'create-service',
                                         '--cli-input-json', json.dumps(service_config)))
        print(f"Created worker service: {result['service']['serviceName']}")
        
        # Setup auto-scaling if enabled
        if self.config['autoscaling']['enabled']:
            self.setup_autoscaling(service_name)
    
    def create_service_registry(self, namespace_id, service_name):
        """Create service registry for service discovery"""
        try:
            result = json.loads(self.aws_cmd('servicediscovery', 'create-service',
                                             '--name', service_name,
                                             '--dns-config', json.dumps({
                                                 "NamespaceId": namespace_id,
                                                 "DnsRecords": [{"Type": "A", "TTL": 60}]
                                             }),
                                             '--health-check-custom-config', 'FailureThreshold=1'))
            return result['Service']['Arn']
        except:
            services = json.loads(self.aws_cmd('servicediscovery', 'list-services'))
            return next(s['Arn'] for s in services['Services'] if s['Name'] == service_name)
    
    def setup_autoscaling(self, service_name):
        """Setup auto-scaling for worker service"""
        print("\n=== Setting Up Auto-Scaling ===")
        
        resource_id = f"service/{self.cluster_name}/{service_name}"
        
        # Register scalable target
        self.aws_cmd('application-autoscaling', 'register-scalable-target',
                    '--service-namespace', 'ecs',
                    '--resource-id', resource_id,
                    '--scalable-dimension', 'ecs:service:DesiredCount',
                    '--min-capacity', str(self.config['ray_worker']['min_count']),
                    '--max-capacity', str(self.config['ray_worker']['max_count']))
        
        # CPU-based scaling policy
        policy_config = {
            "TargetValue": float(self.config['autoscaling']['scale_up_cpu_threshold']),
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
            },
            "ScaleInCooldown": self.config['autoscaling']['scale_down_cooldown'],
            "ScaleOutCooldown": self.config['autoscaling']['scale_up_cooldown']
        }
        
        self.aws_cmd('application-autoscaling', 'put-scaling-policy',
                    '--service-namespace', 'ecs',
                    '--resource-id', resource_id,
                    '--scalable-dimension', 'ecs:service:DesiredCount',
                    '--policy-name', f'{service_name}-cpu-scaling',
                    '--policy-type', 'TargetTrackingScaling',
                    '--target-tracking-scaling-policy-configuration', json.dumps(policy_config))
        
        print("Auto-scaling configured")
    
    def deploy(self):
        """Main deployment workflow"""
        print("Starting Ray on ECS deployment...")
        
        try:
            # Setup network
            if self.config['network']['use_existing']:
                self.vpc_id = self.config['network']['vpc_id']
                self.subnet_ids = self.config['network']['subnet_ids']
                print(f"Using existing VPC: {self.vpc_id}")
                
                # Verify VPC and subnets exist
                try:
                    self.aws_cmd('ec2', 'describe-vpcs', '--vpc-ids', self.vpc_id)
                    self.aws_cmd('ec2', 'describe-subnets', '--subnet-ids', *self.subnet_ids)
                except:
                    print("Error: Existing VPC/subnets not accessible. Creating new VPC...")
                    self.vpc_id, self.subnet_ids = self.create_vpc()
            else:
                self.vpc_id, self.subnet_ids = self.create_vpc()
            
            self.security_group_id = self.create_security_group(self.vpc_id)
            
            # Create IAM roles
            exec_role_arn, task_role_arn = self.create_iam_roles()
            
            # Create ECS cluster
            self.create_ecs_cluster()
            
            # Create service discovery
            namespace_id = self.create_service_discovery()
            
            # Create log group
            log_group = self.create_log_group()
            
            # Register task definitions
            head_task_arn = self.register_head_task_definition(exec_role_arn, task_role_arn, log_group)
            
            # Create head service
            self.create_head_service(head_task_arn, namespace_id)
            
            # Head address for workers
            head_address = f"ray-head.{self.config['service_discovery']['namespace']}"
            
            # Register worker task definition
            worker_task_arn = self.register_worker_task_definition(exec_role_arn, task_role_arn,
                                                                    log_group, head_address)
            
            # Create worker service
            self.create_worker_service(worker_task_arn)
            
            print("\n" + "="*50)
            print("Deployment completed successfully!")
            print("="*50)
            print(f"\nCluster: {self.cluster_name}")
            print(f"Region: {self.region}")
            print(f"\nTo access Ray dashboard, get the head task public IP:")
            print(f"  aws ecs list-tasks --cluster {self.cluster_name} --service-name {self.cluster_name}-head")
            print(f"  Then open: http://<PUBLIC_IP>:8265")
            
        except Exception as e:
            print(f"\nDeployment failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    deployer = RayECSDeployer()
    deployer.deploy()
