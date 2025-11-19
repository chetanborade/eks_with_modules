# Kubernetes Manifests

This directory contains Kubernetes YAML files for deploying your application.

## Structure
```
k8s-manifests/
├── deployment.yaml     # Application deployment
├── service.yaml        # Service configuration
├── configmap.yaml      # Configuration data
├── ingress.yaml        # Ingress rules (optional)
└── README.md          # This file
```

## ArgoCD Integration
ArgoCD will monitor this directory for changes and automatically deploy updates to the EKS cluster.

## Environment Structure
- `dev/` - Development environment configs
- `staging/` - Staging environment configs  
- `prod/` - Production environment configs