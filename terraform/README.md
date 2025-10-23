# EC2 Builder Instance Terraform Configuration

This Terraform configuration creates an EC2 instance named "builder" in the us-east-1 region with Docker support.

## Prerequisites

1. **AWS CLI configured** or AWS credentials available
2. **Terraform installed** (version 1.0+)
3. **No SSH key required** - Terraform will generate one automatically

## Configuration

The configuration uses the following AWS resources:
- **VPC**: Uses existing VPC (vpc-0b110d239f1211b4d)
- **Subnet**: Uses existing public subnet (subnet-0852a4e422a2ea812)
- **Instance Type**: t3.medium (suitable for Docker workloads)
- **AMI**: Latest Amazon Linux 2
- **Security Group**: Configured for secure access with restricted IP ranges

## Files

- `main.tf` - Main Terraform configuration
- `variables.tf` - Variable definitions
- `terraform.tfvars` - Variable values
- `README.md` - This file

## Usage

1. **Initialize Terraform**:
   ```bash
   terraform init
   ```

2. **Plan the deployment**:
   ```bash
   terraform plan
   ```

3. **Apply the configuration**:
   ```bash
   terraform apply
   ```

4. **Connect to the instance**:
   ```bash
   ssh -i builder_key.pem ec2-user@<public-ip>
   ```

## Outputs

After successful deployment, Terraform will output the following information:

### Required Outputs:
- **Instance Public IP**: The public IP address for accessing the instance
- **SSH Key Location**: Path to the private key file for SSH access
- **Security Group ID**: ID of the security group for reference

### Additional Outputs:
- **Instance ID**: AWS EC2 instance identifier
- **Public DNS Name**: DNS name of the instance
- **SSH Key Name**: Name of the AWS key pair
- **SSH Connection Command**: Ready-to-use SSH command

### Example Output:
```
Apply complete! Resources: 4 added, 0 changed, 0 destroyed.

Outputs:

instance_id = "i-1234567890abcdef0"
instance_public_ip = "54.123.45.67"
instance_public_dns = "ec2-54-123-45-67.compute-1.amazonaws.com"
security_group_id = "sg-1234567890abcdef0"
ssh_private_key_path = "/path/to/terraform/builder_key.pem"
ssh_key_name = "builder-key"
ssh_connection = "ssh -i builder_key.pem ec2-user@54.123.45.67"
```

## System Setup

The instance is automatically configured with basic setup through user data script:
- Updates system packages

## Security Group Configuration

The security group is configured with the following rules:

### Inbound Rules:
- **SSH (Port 22)**: Restricted to specified IP range for secure access
- **HTTP (Port 5001)**: Restricted to specified IP range for Python application
- **No other inbound ports** are open for security

### Outbound Rules:
- **All outbound traffic** allowed for software downloads and updates

### Security Best Practices:
- **IP Restriction**: Configure `allowed_ssh_cidr` and `allowed_http_cidr` in `terraform.tfvars`
- **Example**: Set to your specific IP range like `"203.0.113.0/24"`
- **Default**: Currently set to `"0.0.0.0/0"` (all IPs) - **CHANGE THIS FOR PRODUCTION**

## Cleanup

To destroy the resources:
```bash
terraform destroy
```

## SSH Key Management

- **Automatic Generation**: Terraform automatically generates a 4096-bit RSA SSH key pair
- **Private Key Storage**: The private key is saved as `builder_key.pem` in the terraform directory
- **Security**: The private key file has 600 permissions (owner read/write only)
- **Git Protection**: The private key is automatically excluded from version control
- **Connection**: Use the generated private key to connect: `ssh -i builder_key.pem ec2-user@<public-ip>`

## Security Configuration

### IP Restriction Setup:
1. **Find your public IP**: Visit https://whatismyipaddress.com/
2. **Update terraform.tfvars**:
   ```hcl
   allowed_ssh_cidr  = "YOUR_IP/32"  # Example: "203.0.113.1/32"
   allowed_http_cidr = "YOUR_IP/32"  # Example: "203.0.113.1/32"
   ```
3. **For multiple IPs**: Use CIDR notation like `"203.0.113.0/24"`

## Notes

- The instance will be accessible via SSH using the ec2-user account
- Basic system packages will be updated on first boot
- Keep the `builder_key.pem` file secure and never share it
- **IMPORTANT**: Change IP restrictions in `terraform.tfvars` before deploying to production
