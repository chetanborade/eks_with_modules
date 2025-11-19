# EKS Infrastructure

This directory contains Terraform configuration for the EKS cluster and supporting AWS infrastructure.

## Files
- `provider.tf` - AWS provider configuration
- `vpc.tf` - VPC, subnets, and networking
- `eks.tf` - EKS cluster and node groups
- `terraform.tfstate` - Current infrastructure state

## Usage
```bash
cd infrastructure/
terraform init
terraform plan
terraform apply
```

## Cluster Details
- **Cluster Name**: example
- **Region**: ap-south-1 (Mumbai)
- **Kubernetes Version**: 1.31
- **Node Type**: t3.medium
- **Node Count**: 2 (min: 1, max: 3)