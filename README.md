# EKS with CI/CD Pipeline

This is a monorepo containing everything needed for an AWS EKS cluster with a complete CI/CD pipeline using GitHub Actions, ECR, and ArgoCD.

## Project Structure

```
.
├── infrastructure/          # Terraform code for EKS cluster
│   ├── eks.tf              # EKS cluster configuration
│   ├── vpc.tf              # VPC and networking
│   ├── provider.tf         # AWS provider
│   └── README.md           # Infrastructure docs
├── app/                    # Application source code
│   ├── src/                # Source code (to be added)
│   ├── Dockerfile          # Container build (to be added)
│   └── README.md           # App documentation
├── k8s-manifests/          # Kubernetes deployment files
│   ├── deployment.yaml     # App deployment (to be added)
│   ├── service.yaml        # Service config (to be added)
│   └── README.md           # K8s docs
└── .github/workflows/      # CI/CD workflows
    ├── ci.yml              # Build & push to ECR (to be added)
    └── README.md           # Workflow docs
```

## Infrastructure

The EKS cluster is already deployed with:
- **Cluster Name**: example  
- **Region**: ap-south-1 (Mumbai)
- **Kubernetes Version**: 1.31
- **Node Group**: 2x t3.medium instances (auto-scaling 1-3)
- **Networking**: Public subnets with internet gateway

## Next Steps

1. **Connect to cluster**: `aws eks update-kubeconfig --region ap-south-1 --name example`
2. **Add application code** to `app/` directory
3. **Install ArgoCD** on the cluster
4. **Set up GitHub Actions** for CI/CD
5. **Create Kubernetes manifests** for your application

## CI/CD Pipeline Flow

```
Code Push → GitHub Actions → Build Image → Push to ECR → Update K8s Manifests → ArgoCD Sync → Deploy to EKS
```

## Prerequisites

- AWS CLI configured
- kubectl installed  
- Docker installed
- Terraform installed