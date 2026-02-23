# Ray on Amazon ECS Deployment

Automated deployment of Ray cluster on Amazon ECS with Fargate for serverless compute and automatic scaling to zero.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.7+

## Configuration

Edit `config.yaml` to customize your deployment:

### Using Existing VPC
```yaml
network:
  use_existing: true
  vpc_id: vpc-xxxxx
  subnet_ids: [subnet-xxxxx, subnet-yyyyy]
```

### Creating New VPC
```yaml
network:
  use_existing: false
  vpc_cidr: "10.0.0.0/16"
  availability_zones: 2
```

### Launch Type
- **FARGATE**: Serverless, no EC2 management (recommended)
- **EC2**: More control, can use Spot instances

### Ray Cluster Settings
- Adjust CPU/memory for head and worker nodes (in CPU units and MB)
- Configure autoscaling parameters
- Set min/max worker count

## Deployment

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Review and update `config.yaml` with your settings

3. Deploy the stack:
```bash
python deploy.py
```

The deployment will:
- Create/use VPC and networking
- Create security groups
- Create IAM roles for ECS tasks
- Create ECS cluster
- Set up AWS Cloud Map for service discovery
- Deploy Ray head node as ECS service
- Deploy Ray workers as ECS service with auto-scaling

## Accessing Ray Dashboard

1. Get the public IP of the Ray head task:
```bash
# List tasks
aws ecs list-tasks --cluster ray-ecs-cluster --service-name ray-ecs-cluster-head

# Get task details
aws ecs describe-tasks --cluster ray-ecs-cluster --tasks <TASK_ARN>

# Find the public IP in the output
```

2. Open browser to: `http://<PUBLIC_IP>:8265`

## Connecting to Ray Cluster

```python
import ray

# Connect using the head node public IP
ray.init("ray://<PUBLIC_IP>:10001")

# Your Ray code here
@ray.remote
def hello():
    return "Hello from Ray on ECS!"

result = ray.get(hello.remote())
print(result)
```

## Auto-Scaling

The cluster is configured to:
- Scale workers from 0 to max_count based on CPU utilization
- Scale down to 0 after cooldown period of inactivity
- Fargate automatically manages underlying compute

### Scaling Behavior
- Scale up when CPU > 70% (configurable)
- Scale down when CPU < 20% (configurable)
- Scale-in cooldown: 5 minutes (configurable)
- Scale-out cooldown: 1 minute (configurable)

## Cleanup

To remove all resources:
```bash
python cleanup.py
```

This will delete:
- ECS services (head and workers)
- ECS cluster
- Task definitions
- Service discovery namespace
- Security groups
- IAM roles
- VPC and networking (if created by the script)
- CloudWatch log groups

## Cost Optimization

With ECS Fargate and auto-scaling:
- Workers scale to 0 when idle
- Fargate charges only for running tasks
- No EC2 instances to manage
- Pay only for vCPU and memory used

### Estimated Costs (us-east-1)
- Head node (1 vCPU, 2GB): ~$0.04/hour
- Worker node (1 vCPU, 2GB): ~$0.04/hour each
- When scaled to 0 workers: ~$0.04/hour total

## Troubleshooting

Check ECS services:
```bash
aws ecs describe-services --cluster ray-ecs-cluster --services ray-ecs-cluster-head ray-ecs-cluster-worker
```

Check running tasks:
```bash
aws ecs list-tasks --cluster ray-ecs-cluster
aws ecs describe-tasks --cluster ray-ecs-cluster --tasks <TASK_ARN>
```

View logs:
```bash
aws logs tail /ecs/ray-ecs-cluster --follow
```

Check service discovery:
```bash
aws servicediscovery list-namespaces
aws servicediscovery list-services
```

## Advantages over EKS

- **Simpler**: No Kubernetes knowledge required
- **Faster**: Quicker deployment (no cluster provisioning)
- **Cheaper**: No EKS control plane costs ($0.10/hour)
- **Serverless**: Fargate manages all compute
- **Native AWS**: Better integration with AWS services

## Limitations

- No Kubernetes ecosystem
- Less community documentation for Ray on ECS
- Service discovery uses AWS Cloud Map (not Kubernetes DNS)
- Manual scaling policies (no Ray autoscaler integration)
