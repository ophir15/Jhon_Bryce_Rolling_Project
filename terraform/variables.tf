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

variable "vpc_id" {
  description = "VPC ID to use"
  type        = string
  nullable    = false
  validation {
    condition     = length(trimspace(var.vpc_id)) > 0
    error_message = "Provide a valid VPC ID."
  }
}

variable "subnet_id" {
  description = "Subnet ID to use when a single, specific subnet is required"
  type        = string
  default     = null
  nullable    = true
}

variable "subnet_ids" {
  description = "Optional list of subnet IDs to choose from when multiple subnets are acceptable"
  type        = list(string)
  default     = []
}

variable "subnet_tag_filters" {
  description = "Optional map of subnet tag key/value pairs to filter subnets by"
  type        = map(string)
  default     = {}
}

variable "subnet_index" {
  description = "Index of the subnet to use from the resolved subnet list"
  type        = number
  default     = 0
  validation {
    condition     = var.subnet_index >= 0
    error_message = "subnet_index must be zero or a positive integer."
  }
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access"
  type        = string
  nullable    = false
  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0)) && var.allowed_ssh_cidr != "0.0.0.0/0"
    error_message = "SSH access cannot be open to the Internet. Provide a restricted CIDR block."
  }
}

variable "allowed_http_cidr" {
  description = "CIDR block allowed for HTTP access on port 5001"
  type        = string
  nullable    = false
  validation {
    condition     = can(cidrhost(var.allowed_http_cidr, 0)) && var.allowed_http_cidr != "0.0.0.0/0"
    error_message = "HTTP access cannot be wide open. Provide a restricted CIDR block."
  }
}
