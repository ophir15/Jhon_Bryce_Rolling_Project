variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_name" {
  description = "Name of the AWS key pair"
  type        = string
  default     = "builder-key"
}

variable "key_algorithm" {
  description = "Algorithm for SSH key generation"
  type        = string
  default     = "RSA"
}

variable "key_rsa_bits" {
  description = "Number of bits for RSA key"
  type        = number
  default     = 4096
}

variable "vpc_id" {
  description = "VPC ID to use"
  type        = string
  default     = "vpc-0b110d239f1211b4d"
}

variable "subnet_id" {
  description = "Subnet ID to use"
  type        = string
  default     = "subnet-0852a4e422a2ea812"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access"
  type        = string
  default     = "0.0.0.0/0"  # Change this to your specific IP range for security
}

variable "allowed_http_cidr" {
  description = "CIDR block allowed for HTTP access on port 5001"
  type        = string
  default     = "0.0.0.0/0"  # Change this to your specific IP range for security
}
