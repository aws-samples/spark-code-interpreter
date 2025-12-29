# Lambda Function
resource "aws_lambda_function" "spark_lambda" {
  function_name = "sparkOnLambda-${var.stack_name}"
  description   = "Lambda to run spark containers"
  
  package_type = "Image"
  image_uri    = var.image_uri
  
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory
  role        = aws_iam_role.spark_lambda_role.arn

  image_config {
    command = ["/var/task/sparkLambdaHandler.lambda_handler"]
  }

  tags = {
    Name = "SparkOnLambda"
  }
}

# EC2 Instance
resource "aws_instance" "main" {
  instance_type               = var.instance_type
  ami                        = data.aws_ssm_parameter.ami.value
  subnet_id                  = aws_subnet.public.id
  vpc_security_group_ids     = [aws_security_group.main.id]
  iam_instance_profile       = aws_iam_instance_profile.instance_profile.name
  associate_public_ip_address = true

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    git_repo      = var.git_repo
    git_branch    = var.git_branch
    aws_region    = data.aws_region.current.name
    aws_account_id = data.aws_caller_identity.current.account_id
  }))

  tags = {
    Name = "BluebearAppEC2"
  }
}