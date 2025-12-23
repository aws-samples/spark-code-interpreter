output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.main.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance (replace 'your-key.pem' with your private key file)"
  value       = "ssh -i your-key.pem ubuntu@${aws_instance.main.public_ip}"
}

output "streamlit_url" {
  description = "URL to access the Bluebear Streamlit app"
  value       = "http://${aws_instance.main.public_ip}:8501"
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for Bedrock data"
  value       = aws_s3_bucket.main.id
}

output "chat_data_bucket_name" {
  description = "Name of the S3 bucket for chat data"
  value       = aws_s3_bucket.chat_data.id
}

output "chat_history_table_name" {
  description = "Name of the DynamoDB table for chat history"
  value       = aws_dynamodb_table.chat_history.name
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.spark_lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.spark_lambda.arn
}