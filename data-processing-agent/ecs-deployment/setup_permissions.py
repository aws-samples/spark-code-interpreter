#!/usr/bin/env python3
"""Setup IAM permissions for Ray ECS cluster management"""

import json
import subprocess
import sys
import yaml

def run_cmd(cmd):
    """Execute shell command"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def get_current_user():
    """Get current IAM user or role"""
    stdout, code = run_cmd(['aws', 'sts', 'get-caller-identity'])
    if code != 0:
        print("Error getting caller identity")
        sys.exit(1)
    identity = json.loads(stdout)
    return identity

def create_ray_admin_policy():
    """Create IAM policy for Ray cluster administration"""
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ECSFullAccess",
                "Effect": "Allow",
                "Action": [
                    "ecs:*",
                    "ecr:*"
                ],
                "Resource": "*"
            },
            {
                "Sid": "EC2NetworkAccess",
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeVpcs",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:CreateSecurityGroup",
                    "ec2:DeleteSecurityGroup",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:CreateTags",
                    "ec2:CreateVpc",
                    "ec2:DeleteVpc",
                    "ec2:CreateSubnet",
                    "ec2:DeleteSubnet",
                    "ec2:CreateInternetGateway",
                    "ec2:DeleteInternetGateway",
                    "ec2:AttachInternetGateway",
                    "ec2:DetachInternetGateway",
                    "ec2:DescribeRouteTables",
                    "ec2:CreateRoute",
                    "ec2:DeleteRoute",
                    "ec2:ModifyVpcAttribute",
                    "ec2:ModifySubnetAttribute",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeInternetGateways"
                ],
                "Resource": "*"
            },
            {
                "Sid": "IAMRoleAccess",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:GetRole",
                    "iam:PassRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:ListAttachedRolePolicies",
                    "iam:CreatePolicy",
                    "iam:DeletePolicy",
                    "iam:GetPolicy"
                ],
                "Resource": "*"
            },
            {
                "Sid": "ServiceDiscoveryAccess",
                "Effect": "Allow",
                "Action": [
                    "servicediscovery:*"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchLogsAccess",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:DeleteLogGroup",
                    "logs:DescribeLogGroups",
                    "logs:PutRetentionPolicy",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents"
                ],
                "Resource": "*"
            },
            {
                "Sid": "ApplicationAutoScalingAccess",
                "Effect": "Allow",
                "Action": [
                    "application-autoscaling:*"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchMetricsAccess",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricAlarm",
                    "cloudwatch:DeleteAlarms",
                    "cloudwatch:DescribeAlarms"
                ],
                "Resource": "*"
            }
        ]
    }
    
    policy_name = "RayECSAdminPolicy"
    
    # Try to create policy
    stdout, code = run_cmd([
        'aws', 'iam', 'create-policy',
        '--policy-name', policy_name,
        '--policy-document', json.dumps(policy_document),
        '--description', 'Policy for Ray ECS cluster administration'
    ])
    
    if code == 0:
        policy = json.loads(stdout)
        policy_arn = policy['Policy']['Arn']
        print(f"Created policy: {policy_arn}")
    else:
        # Policy might already exist, get it
        identity = get_current_user()
        account_id = identity['Account']
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        print(f"Policy already exists: {policy_arn}")
    
    return policy_arn

def attach_policy_to_user(policy_arn, user_name):
    """Attach policy to IAM user"""
    stdout, code = run_cmd([
        'aws', 'iam', 'attach-user-policy',
        '--user-name', user_name,
        '--policy-arn', policy_arn
    ])
    
    if code == 0:
        print(f"Attached policy to user: {user_name}")
        return True
    else:
        print(f"Error attaching policy to user: {stdout}")
        return False

def attach_policy_to_role(policy_arn, role_name):
    """Attach policy to IAM role"""
    stdout, code = run_cmd([
        'aws', 'iam', 'attach-role-policy',
        '--role-name', role_name,
        '--policy-arn', policy_arn
    ])
    
    if code == 0:
        print(f"Attached policy to role: {role_name}")
        return True
    else:
        print(f"Error attaching policy to role: {stdout}")
        return False

def main():
    print("Setting up IAM permissions for Ray ECS cluster...")
    
    # Get current identity
    identity = get_current_user()
    print(f"\nCurrent identity: {identity['Arn']}")
    
    # Create admin policy
    policy_arn = create_ray_admin_policy()
    
    # Attach to user or role
    if 'user' in identity['Arn']:
        user_name = identity['Arn'].split('/')[-1]
        attach_policy_to_user(policy_arn, user_name)
    elif 'assumed-role' in identity['Arn']:
        role_name = identity['Arn'].split('/')[-2]
        attach_policy_to_role(policy_arn, role_name)
    else:
        print("Warning: Could not determine user or role type")
        print(f"Please manually attach policy: {policy_arn}")
    
    print("\n" + "="*50)
    print("Permissions setup completed!")
    print("="*50)
    print(f"\nPolicy ARN: {policy_arn}")
    print("\nYou can now run: python deploy.py")

if __name__ == '__main__':
    main()
