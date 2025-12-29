variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "git_repo" {
  description = "Git repository URL to clone"
  type        = string
  default     = "https://github.com/aws-samples/spark-code-interpreter.git"
}

variable "image_uri" {
  description = "ECR URI for the SparkOnLambda image - REQUIRED (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/spark-lambda:latest)"
  type        = string
  
  validation {
    condition     = length(var.image_uri) > 0
    error_message = "ECR image URI is required and cannot be empty."
  }
}

variable "lambda_timeout" {
  description = "Maximum Lambda invocation runtime in seconds (min 1 - 900 max)"
  type        = number
  default     = 900
  
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "lambda_memory" {
  description = "Lambda memory in MB (min 128 - 10,240 max)"
  type        = number
  default     = 3008
  
  validation {
    condition     = var.lambda_memory >= 128 && var.lambda_memory <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "ec2_ami_id" {
  description = "EC2 AMI Id to host the bedrock chat agent"
  type        = string
  default     = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
}

variable "git_branch" {
  description = "Git branch for Interpreter"
  type        = string
  default     = "feature/sloanintegration"
}

variable "dynamodb_table" {
  description = "DynamoDB table name - must be unique within your AWS account and region"
  type        = string
  
  validation {
    condition     = length(var.dynamodb_table) > 0 && length(var.dynamodb_table) <= 255
    error_message = "DynamoDB table name must be between 1 and 255 characters."
  }
}

variable "user_id" {
  description = "User ID"
  type        = string
}

variable "bucket_name" {
  description = "Main bucket name - must be globally unique across all AWS accounts"
  type        = string
  
  validation {
    condition     = length(var.bucket_name) >= 3 && length(var.bucket_name) <= 63
    error_message = "S3 bucket name must be between 3 and 63 characters."
  }
}

variable "input_bucket" {
  description = "Input bucket name - must be globally unique across all AWS accounts"
  type        = string
  
  validation {
    condition     = length(var.input_bucket) >= 3 && length(var.input_bucket) <= 63
    error_message = "S3 bucket name must be between 3 and 63 characters."
  }
}

variable "input_s3_path" {
  description = "Input S3 path"
  type        = string
}

variable "lambda_function" {
  description = "Lambda function name"
  type        = string
}

variable "my_ip" {
  description = "Your IP address in CIDR notation (e.g., 1.2.3.4/32) - REQUIRED for security group access"
  type        = string
  
  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/32$", var.my_ip))
    error_message = "IP address must be in CIDR notation with /32 suffix (e.g., 1.2.3.4/32)."
  }
}

variable "stack_name" {
  description = "Stack name for resource naming"
  type        = string
  default     = "spark-interpreter"
}