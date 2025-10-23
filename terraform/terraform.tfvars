aws_region     = "us-east-1"
instance_type  = "t3.medium"
key_name       = "builder-key"
key_algorithm  = "RSA"
key_rsa_bits   = 4096
vpc_id         = "vpc-0b110d239f1211b4d"
subnet_id      = "subnet-0852a4e422a2ea812"

# Security Configuration
# IMPORTANT: Change these to your specific IP ranges for security
allowed_ssh_cidr  = "0.0.0.0/0"  # Example: "203.0.113.0/24" for specific range
allowed_http_cidr = "0.0.0.0/0"  # Example: "203.0.113.0/24" for specific range
