# Configure the AWS Provider
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4.0"
    }
  }
}

provider "aws" {
  region     = var.aws_region
}

# Data source to get the latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Use existing VPC and subnet
data "aws_vpc" "existing" {
  id = var.vpc_id
}

# Create security group for builder instance
resource "aws_security_group" "builder_sg" {
  name_prefix = "builder-sg"
  vpc_id      = data.aws_vpc.existing.id

  # SSH access (port 22) - restricted to specific IP range
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
    description = "SSH access"
  }

  # HTTP access (port 5001) for Python application - restricted to specific IP range
  ingress {
    from_port   = 5001
    to_port     = 5001
    protocol    = "tcp"
    cidr_blocks = [var.allowed_http_cidr]
    description = "HTTP access for Python application"
  }

  # All outbound traffic for software downloads and updates
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "builder-security-group"
  }
}

# Generate an SSH key pair
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Save the private key locally
resource "local_sensitive_file" "private_key" {
  filename        = "${path.module}/builder_key.pem"
  content         = tls_private_key.ssh_key.private_key_pem
  file_permission = "0600"
}

# Save SSH key information as a text file
resource "local_file" "ssh_key_info" {
  content = <<-EOT
SSH Key Information
==================

Private Key File: ${local_sensitive_file.private_key.filename}
Public Key: ${tls_private_key.ssh_key.public_key_openssh}
AWS Key Pair Name: ${aws_key_pair.builder_key.key_name}

Connection Information:
- Instance Public IP: ${aws_instance.builder.public_ip}
- Instance Public DNS: ${aws_instance.builder.public_dns}
- SSH Command: ssh -i ${local_sensitive_file.private_key.filename} ec2-user@${aws_instance.builder.public_ip}

Security Notes:
- Private key file permissions set to 0600 (readable only by owner)
- Keep the private key secure and do not share it
- The public key has been uploaded to AWS as key pair: ${aws_key_pair.builder_key.key_name}
EOT
  filename        = "${path.module}/ssh_key_info.txt"
  file_permission = "0644"
}

# Create an AWS key pair using the public key
resource "aws_key_pair" "builder_key" {
  key_name   = var.key_name
  public_key = tls_private_key.ssh_key.public_key_openssh
}

data "aws_subnets" "available" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }

  dynamic "filter" {
    for_each = var.subnet_tag_filters
    content {
      name   = "tag:${filter.key}"
      values = [filter.value]
    }
  }
}

locals {
  single_subnet      = var.subnet_id != null ? [var.subnet_id] : []
  candidate_subnets  = length(var.subnet_ids) > 0 ? var.subnet_ids : (length(local.single_subnet) > 0 ? local.single_subnet : data.aws_subnets.available.ids)
  selected_subnet_id = try(element(local.candidate_subnets, var.subnet_index), null)
}

# Create EC2 instance
resource "aws_instance" "builder" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.builder_key.key_name
  vpc_security_group_ids = [aws_security_group.builder_sg.id]
  subnet_id             = local.selected_subnet_id

  # User data script for basic setup
  user_data = <<-EOF
    #!/bin/bash
    yum update -y
  EOF

  tags = {
    Name = "builder"
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted = true
  }

  lifecycle {
    precondition {
      condition     = local.selected_subnet_id != null && length(local.candidate_subnets) > var.subnet_index
      error_message = "subnet_index ${var.subnet_index} is out of range for the resolved subnet list (size ${length(local.candidate_subnets)})."
    }
  }
}

# Output values
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.builder.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.builder.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.builder.public_dns
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.builder_sg.id
}

output "ssh_private_key_path" {
  value       = local_sensitive_file.private_key.filename
  description = "Path to the generated private SSH key"
  sensitive   = true
}

output "ssh_key_name" {
  value       = aws_key_pair.builder_key.key_name
  description = "Name of the AWS SSH key pair"
}

output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh -i ${local_sensitive_file.private_key.filename} ec2-user@${aws_instance.builder.public_ip}"
}

output "ssh_key_info_file" {
  description = "Path to the SSH key information text file"
  value       = local_file.ssh_key_info.filename
}
