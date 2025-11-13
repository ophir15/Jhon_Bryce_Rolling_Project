aws_region    = "us-east-1"
instance_type = "t3.medium"
key_name      = "builder-key"
vpc_id        = "vpc-0b110d239f1211b4d"
subnet_id     = "subnet-0852a4e422a2ea812"

# Security Configuration
# IMPORTANT: Replace the documentation IP ranges below with your own trusted sources.
allowed_ssh_cidr  = "203.0.113.10/32"
allowed_http_cidr = "203.0.113.0/28"
