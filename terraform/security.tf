# Security Group
resource "aws_security_group" "main" {
  name_prefix = "bluebear-sg-"
  description = "Allow SSH and Streamlit traffic"
  vpc_id      = aws_vpc.main.id

  # SSH access from user IP
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
    description = "SSH access from user IP"
  }

  # HTTPS access from user IP
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
    description = "HTTPS access from user IP"
  }

  # Streamlit access from user IP
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
    description = "Streamlit access from user IP"
  }

  # SSH access from EC2 Instance Connect - US East (Ohio)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["3.16.146.0/29"]
    description = "EC2 Instance Connect - US East (Ohio)"
  }

  # SSH access from EC2 Instance Connect - US East (N. Virginia)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["18.206.107.24/29"]
    description = "EC2 Instance Connect - US East (N. Virginia)"
  }

  # SSH access from EC2 Instance Connect - Europe (Frankfurt)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["3.120.181.40/29"]
    description = "EC2 Instance Connect - Europe (Frankfurt)"
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "BluebearSecurityGroup"
  }
}