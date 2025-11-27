# EKS Cluster outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster for the OpenID Connect identity provider"
  value       = module.eks.cluster_oidc_issuer_url
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider if enabled."
  value       = module.eks.oidc_provider_arn
}

# S3 bucket outputs
output "velero_bucket_name" {
  description = "Name of S3 bucket for Velero backups"
  value       = aws_s3_bucket.velero_backup.bucket
}

output "velero_bucket_arn" {
  description = "ARN of S3 bucket for Velero backups"
  value       = aws_s3_bucket.velero_backup.arn
}

# Useful for IRSA setup
output "aws_region" {
  description = "AWS region"
  value       = "ap-south-1"
}

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "oidc_id" {
  description = "OIDC Provider ID (for IRSA trust policies)"
  value       = replace(module.eks.cluster_oidc_issuer_url, "https://oidc.eks.ap-south-1.amazonaws.com/id/", "")
}

# Data source to get current AWS account ID
data "aws_caller_identity" "current" {}