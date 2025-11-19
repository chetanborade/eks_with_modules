# CI/CD Workflows

This directory contains GitHub Actions workflow files for CI/CD automation.

## Workflows
- `ci.yml` - Continuous Integration (build, test, push to ECR)
- `cd.yml` - Continuous Deployment (update k8s manifests)
- `infrastructure.yml` - Terraform infrastructure updates (optional)

## Secrets Required
Configure these secrets in GitHub repository settings:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY` 
- `AWS_REGION`
- `EKS_CLUSTER_NAME`
- `ECR_REPOSITORY`