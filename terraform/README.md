# Terraform Infrastructure for Spark Code Interpreter

This Terraform configuration creates the same infrastructure as the CloudFormation template, including:

- VPC with public subnet and internet gateway
- EC2 instance running Streamlit application
- Lambda function for Spark processing
- DynamoDB table for chat history
- Two S3 buckets for data storage
- IAM roles and policies

## Prerequisites

1. **Terraform**: Install Terraform >= 1.0
2. **AWS CLI**: Configure AWS credentials
3. **ECR Image**: Build and push the Spark Lambda container image to ECR

## Usage

1. **Copy and customize the variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars with your actual values:**
   ```bash
   # REQUIRED: Replace these placeholder values
   my_ip = "YOUR_ACTUAL_IP/32"           # e.g., "203.0.113.1/32"
   image_uri = "YOUR_ECR_IMAGE_URI"      # e.g., "123456789012.dkr.ecr.us-east-1.amazonaws.com/spark-lambda:latest"
   
   # REQUIRED: Make these globally unique
   bucket_name = "your-unique-main-bucket-name"
   input_bucket = "your-unique-input-bucket-name"
   dynamodb_table = "your-unique-table-name"
   ```

3. **Get your IP address:**
   ```bash
   curl -s https://checkip.amazonaws.com
   # Add /32 to the end for CIDR notation
   ```

3. **Initialize Terraform:**
   ```bash
   terraform init
   ```

4. **Plan the deployment:**
   ```bash
   terraform plan
   ```

5. **Apply the configuration:**
   ```bash
   terraform apply
   ```

6. **Access the application:**
   - The Streamlit app will be available at the URL shown in the outputs
   - SSH access is available using EC2 Instance Connect or your IP

## Important Variables

- `my_ip`: **REQUIRED** - Your IP address in CIDR notation for security group access (e.g., "1.2.3.4/32")
- `image_uri`: **REQUIRED** - ECR URI for the Spark Lambda container image (e.g., "123456789012.dkr.ecr.us-east-1.amazonaws.com/spark-lambda:latest")
- `bucket_name` and `input_bucket`: Must be globally unique S3 bucket names (add a unique suffix)
- `dynamodb_table`: Must be unique within your AWS account and region

## Security Notes

- **Never commit terraform.tfvars** to version control as it contains sensitive information
- Add `terraform.tfvars` to your `.gitignore` file
- The placeholder IP "YOUR_IP_ADDRESS/32" in the example will not work - you must replace it with your actual IP
- Ensure ECR image exists before running terraform apply

## Outputs

After deployment, Terraform will output:
- EC2 public IP address
- Streamlit application URL
- SSH connection command
- Resource names (buckets, tables, Lambda function)

## Cleanup

To destroy all resources:
```bash
terraform destroy
```

## File Structure

- `main.tf`: Provider configuration and data sources
- `variables.tf`: Input variables
- `networking.tf`: VPC, subnets, and routing
- `security.tf`: Security groups
- `storage.tf`: S3 buckets and DynamoDB table
- `iam.tf`: IAM roles and policies
- `compute.tf`: EC2 instance and Lambda function
- `outputs.tf`: Output values
- `user_data.sh`: EC2 initialization script