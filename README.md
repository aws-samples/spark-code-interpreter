# Project Bluebear - Big Data for Business Users
Project Bluebear is a cutting-edge conversational Gen AI solution designed to analyze datasets ranging from megabytes (MBs) to petabytes (PBs) using Amazon Bedrock Agents and Apache Spark. This framework provides two seamless execution options:

* Spark on AWS Lambda (SoAL) – A lightweight, real-time processing engine for datasets up to 500MB, supporting single-node spark execution for optimized performance.

* Amazon EMR Serverless – A scalable solution for handling larger datasets, ensuring efficient heavy-lifting for extensive data analysis.

## How It Works

* Conversational Interface – Business users submit natural language queries.

* AI-Powered Code Generation – Amazon Bedrock dynamically generates Spark code based on the user’s prompt.

* Intelligent Execution – The Spark code runs on a dropdown interface, allowing users to choose between SoAL (Spark on AWS Lambda) and Amazon EMR Serverless, providing a cost-conscious option for executing their queries.

    * SoAL (Spark on AWS Lambda) for quick, real-time analysis of smaller datasets.

    * Amazon EMR Serverless for processing larger datasets, including petabytes of data, with robust computational power.

## Solving a Critical Pain Point

Natural language should be the new way of interacting with data, eliminating the need to spend months on ETL frameworks and deployment. Project Bluebear enables business users to perform analytics effortlessly through natural language queries, providing actionable insights in real time or at scale.


<img src="images/image-v1.png" width="1000"/>

## Architecture
This project provides a conversational interface using [Bedrock Claude Chatbot](https://github.com/aws-samples/bedrock-claude-chatbot). Amazon Bedrock is used for generating the spark code based on the user prompt. The spark code is then run on a lightweight [Apache Spark on AWS Lambda(SoAL) framework](https://github.com/aws-samples/spark-on-aws-lambda) to provide analysis results to the user. If the input data file is small (<=500 MB), Spark on AWS Lambda (SoAL) is used for data processing. If the input data file is larger, Amazon EMR Serverless is used for data processing. SoAL helps with quick data processing and can provide the results in realtime. With Amazon EMR Serverless, users will receive results once the data processing is finished based on the size of the input data set.

<img src="images/Architecture Numbered Streamlit.jpeg" width="1000"/>

## Pre-Requisites
1. [Amazon Bedrock Anthropic Claude Model Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
2. [S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html) to store uploaded documents and Textract output.
3. [Amazon Elastic Container Registry](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html) to store custom docker images.
4. [Setup Spark on AWS Lambda](https://github.com/aws-samples/spark-on-aws-lambda/wiki/Cloudformation) to setup Spark on AWS lambda can be used as code interpreter.
5. Optional:
    - Create an Amazon DynamoDB table to store chat history (Run the notebook **BedrockChatUI** to create a DynamoDB Table). This is optional as there is a local disk storage option, however, I would recommend using Amazon DynamoDB.
    - Amazon Textract. This is optional as there is an option to use python libraries [`pypdf2`](https://pypi.org/project/PyPDF2/) and [`pytessesract`](https://pypi.org/project/pytesseract/) for PDF and image processing. However, I would recommend using Amazon Textract for higher quality PDF and image processing. You will experience latency when using `pytesseract`.

To use the **Advanced Analytics Feature**, this additional step is required (ChatBot can still be used without enabling `Advanced Analytics Feature`):

5. [Amazon Lambda](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-clients) function with custom python image to execute python code for analytics.
    - Create an private ECR repository by following the link in step 3.
    - On your local machine or any related AWS services including [AWS CloudShell](https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html), [Amazon Elastic Compute Cloud](https://aws.amazon.com/ec2/getting-started/), [Amazon Sageamker Studio](https://aws.amazon.com/blogs/machine-learning/accelerate-ml-workflows-with-amazon-sagemaker-studio-local-mode-and-docker-support/) etc. run the following CLI commands:
        - install git and clone this git repo `git clone [github_link]`
        - navigate into the Docker directory `cd Docker`
        - if using local machine, authenticate with your [AWS credentials](https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-authentication.html)
        - install [AWS Command Line Interface (AWS CLI) version 2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) if not already installed.
        - Follow the steps in the **Deploying the image** section under **Using an AWS base image for Python** in this [documentation guide](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-instructions). Replace the placeholders with the appropiate values. You can skip step `2` if you already created an ECR repository.
        - In step 6, in addition to `AWSLambdaBasicExecutionRole` policy, **ONLY** grant [least priveledged read and write Amazon S3 policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_examples_s3_rw-bucket.html) to the execution role. Scope down the policy to only include the necessary S3 bucket and S3 directory prefix where uploaded files will be stored and read from as configured in the `config.json` file below.
        - In step 7, I recommend creating the Lambda function in a [Amazon Virtual Private Cloud (VPC)](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html) without [internet access](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-example-private-subnets-nat.html) and attach Amazon S3 and Amazon CloudWatch [gateway](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html) and [interface endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#create-interface-endpoint.html) accordingly. The following step 7 command can be modified to include VPC paramters:
        ```
        aws lambda create-function \
            --function-name YourFunctionName \
            --package-type Image \
            --code ImageUri=your-account-id.dkr.ecr.your-region.amazonaws.com/your-repo:tag \
            --role arn:aws:iam::your-account-id:role/YourLambdaExecutionRole \
            --vpc-config SubnetIds=subnet-xxxxxxxx,subnet-yyyyyyyy,SecurityGroupIds=sg-zzzzzzzz \
            --memory-size 512 \
            --timeout 300 \
            --region your-region
        ``````

        Modify the placeholders as appropiate. I recommend to keep `timeout` and `memory-size` params conservative as that will affect cost. A good staring point for memory is `512` MB.
        - Ignore step 8.
        
**⚠ IMPORTANT SECURITY NOTE:**

Enabling the **Advanced Analytics Feature** allows the LLM to generate and execute Python code to analyze your dataset that will automatically be executed in a Lambda function environment. To mitigate potential risks:

1. **VPC Configuration**: 
- It is recommended to place the Lambda function in an internet-free VPC.
- Use Amazon S3 and CloudWatch gateway/interface endpoints for necessary access.

2. **IAM Permissions**: 
- Scope down the Lambda execution role to only Amazon S3 and the required S3 resources. This is in addition to `AWSLambdaBasicExecutionRole` policy.

3. **Library Restrictions**: 
- Only libraries specified in `Docker/requirements.txt` will be available at runtime.
- Modify this list carefully based on your needs.

4. **Resource Allocation**: 
- Adjust Lambda `timeout` and `memory-size` based on data size and analysis complexity.

5. **Production Considerations**: 
- This application is designed for POC use.
- Implement additional security measures before deploying to production.

The goal is to limit the potential impact of generated code execution.

## Configuration
To customize the behavior for the conversational chatbot follow [these](https://github.com/aws-samples/bedrock-claude-chatbot/tree/main?tab=readme-ov-file#configuration) instructions.


## Configuration
To customize the chatbot’s behavior, follow these configuration instructions:

* Modify config.json to specify your S3 bucket, Lambda function, and Bedrock region.

* Ensure the correct AWS region is set to avoid connectivity issues.

* Only update the necessary parameters, as other settings remain static.


```json
{
  "s3_bucket": "your-s3-bucket",
  "lambda_function": "your-lambda-function",
  "bedrock_region": "us-east-1"
}
```
# Quick Start Guide - Ray + Spark Platform

## 🚀 **5-Minute Quick Start**

### **1. Prerequisites Check**
```bash
cd terraform-ray-infrastructure
./validate-prerequisites.sh
```

**If any checks fail**, refer to [`PREREQUISITES.md`](./PREREQUISITES.md) for detailed setup.

### **2. Configure Deployment**
```bash
cp terraform.tfvars.example terraform.tfvars
```

**Minimal required changes in `terraform.tfvars`:**
```hcl
# Set your AWS region
aws_region = "us-east-1"

# Set environment name
environment = "dev"

# IMPORTANT: Set your IP address for security
allowed_cidr_blocks = ["YOUR.IP.ADDRESS/32"]
```

**Get your IP:**
```bash
curl -s https://checkip.amazonaws.com
# Example: 203.0.113.45
# Use: ["203.0.113.45/32"]
```

### **3. Deploy Infrastructure**
```bash
./deploy.sh
```

**Deployment takes ~15-20 minutes**

### **4. Access Your Platform**
After deployment completes:
```bash
# Get access URLs
terraform output

# Test the platform
./test-suite.sh
```

---

## 📋 **What Gets Deployed**

### **Compute Infrastructure**
- **EKS Cluster**: Kubernetes cluster for Ray distributed computing
- **ECS Fargate**: Serverless containers for React + FastAPI
- **Lambda Functions**: Spark on Lambda for small datasets
- **EMR Serverless**: Auto-scaling Spark for large datasets

### **Data & Storage**
- **S3 Buckets**: Data lake for both Spark and Ray workloads
- **DynamoDB**: Chat history and session storage
- **AWS Glue**: Data catalog and metadata management

### **AI/ML Integration**
- **Bedrock AgentCore**: AI agents for code generation
- **MCP Gateway**: Model-Computer Protocol for validation
- **Claude Sonnet 4**: Advanced code generation AI

### **Networking & Security**
- **VPC with Public/Private Subnets**: Secure network architecture
- **Application Load Balancer**: High-availability load balancing
- **Security Groups**: Least-privilege access control
- **NAT Gateways**: Secure outbound internet access

---

## 🎯 **Access Points After Deployment**

| Service | URL | Purpose |
|---------|-----|---------|
| **React App** | `http://your-alb-url.amazonaws.com` | Main user interface |
| **FastAPI Backend** | `http://your-alb-url.amazonaws.com/api` | Unified Spark/Ray API |
| **Ray Dashboard** | `http://ray-public-ip:8265` | Ray cluster monitoring |
| **EKS Dashboard** | Via kubectl port-forward | Kubernetes management |

---

## 💰 **Cost Estimate**

| Environment | Monthly Cost | Resources |
|-------------|--------------|-----------|
| **Development** | $273-400 | Minimal resources, spot instances |
| **Staging** | $350-500 | Moderate resources, mixed instances |
| **Production** | $400-643 | Full redundancy, on-demand instances |

**Cost optimization tips:**
- Use `enable_spot_instances = true` for dev/staging
- Set `log_retention_days = 7` for development
- Adjust `eks_node_desired_size` based on usage

---

## 🔧 **Common Configurations**

### **Development Environment**
```hcl
environment = "dev"
eks_node_desired_size = 1
eks_node_max_size = 3
ray_worker_max_replicas = 2
enable_spot_instances = true
log_retention_days = 7
```

### **Production Environment**
```hcl
environment = "prod"
eks_node_desired_size = 3
eks_node_max_size = 10
ray_worker_max_replicas = 8
enable_spot_instances = false
log_retention_days = 30
domain_name = "ray.yourcompany.com"
```

---

## 🧪 **Testing Your Deployment**

### **Quick Health Check**
```bash
# Backend API
curl http://your-alb-url/health

# Ray status
curl http://your-alb-url/api/ray/status

# Spark status
curl http://your-alb-url/api/spark/status
```

### **Complete Test Suite**
```bash
./test-suite.sh all
```

### **Manual Testing**
1. **Open React App**: Navigate to your application URL
2. **Submit Ray Job**: Test distributed computing workload
3. **Submit Spark Job**: Test data processing (small file → Lambda, large file → EMR)
4. **Check Ray Dashboard**: Monitor cluster performance

---

## 🆘 **Troubleshooting**

### **Deployment Failed**
```bash
# Check Terraform state
terraform show

# View detailed error logs
terraform apply -auto-approve -detailed-exitcode

# For specific component failures
terraform apply -target=module.eks
```

### **Application Not Accessible**
```bash
# Check ALB health
aws elbv2 describe-target-health --target-group-arn $(terraform output -raw alb_target_group_arn)

# Check ECS service status
aws ecs describe-services --cluster $(terraform output -raw ecs_cluster_name) --services ray-backend
```

### **Ray Cluster Issues**
```bash
# Configure kubectl
aws eks update-kubeconfig --region $(terraform output -raw aws_region) --name $(terraform output -raw eks_cluster_id)

# Check Ray pods
kubectl get pods -n ray-system

# View Ray logs
kubectl logs -n ray-system -l app=ray-head
```

---

## 🔄 **Updates & Maintenance**

### **Update Application Code**
```bash
# Rebuild and push new images
./deploy.sh

# Or update specific services
terraform apply -target=module.ecs
```

### **Scale Resources**
```bash
# Edit terraform.tfvars
ray_worker_max_replicas = 10
eks_node_max_size = 15

# Apply changes
terraform apply
```

### **Backup Important Data**
```bash
# Backup S3 data
aws s3 sync s3://$(terraform output -raw s3_data_bucket_name) ./backup/

# Export DynamoDB
aws dynamodb scan --table-name $(terraform output -raw dynamodb_table_name) > backup/chat-history.json
```

---

## 🧹 **Cleanup**

### **Destroy Everything**
```bash
./deploy.sh destroy
```

### **Selective Cleanup**
```bash
# Remove only EKS cluster
terraform destroy -target=module.eks

# Remove only Ray cluster
terraform destroy -target=module.ray_cluster
```

---

## 📚 **Additional Documentation**

- [`PREREQUISITES.md`](./PREREQUISITES.md) - Detailed dependency setup
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - System architecture overview
- [`DEPLOYMENT-CHECKLIST.md`](./DEPLOYMENT-CHECKLIST.md) - Step-by-step deployment guide
- [`README.md`](./README.md) - Comprehensive documentation

---

## 🎉 **Success!**

Once deployed, you'll have a **production-grade, unified Spark + Ray platform** that can:

✅ **Process small datasets** in real-time with Spark on Lambda
✅ **Handle big data** with auto-scaling EMR Serverless
✅ **Run distributed ML/AI** workloads on Ray cluster
✅ **Provide modern React interface** for natural language queries
✅ **Scale automatically** based on demand
✅ **Integrate with AWS services** seamlessly

**Ready to revolutionize your data processing workflows!** 🚀
## Future Road Map
We have below items on future roadmap
* In case of a larger dataset, use subset of the dataset to provide realtime results back to the user.
* Automatically decide weather to use SoAL or EMR serverless based on the size of the dataset.

## Cleanup
Terminate the EC2 instance
