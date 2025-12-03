# Karpenter Installation and Configuration Steps

## Overview
This document outlines the complete process for installing and configuring Karpenter on an existing EKS cluster. All critical fixes have been integrated into the appropriate steps to ensure a successful first-time installation.

## Prerequisites
- EKS cluster running and accessible via kubectl
- AWS CLI configured with appropriate permissions
- Helm installed (for Karpenter installation)
- kubectl configured to access the cluster

## Step 1: Pre-Installation Planning and Resource Preparation

### 1.1 Verify Cluster Status
Check that your EKS cluster is running and accessible.
```bash
kubectl get nodes
kubectl get pods -A
```

### 1.2 Get Required Information
Get the information you'll need for IAM role configuration.
```bash
# Get cluster name
kubectl config current-context

# Get AWS account ID  
aws sts get-caller-identity --query Account --output text

# Get OIDC issuer URL (needed for Controller role trust policy)
aws eks describe-cluster --name YOUR_CLUSTER_NAME --query cluster.identity.oidc.issuer --output text

# Get OIDC ID (extract from issuer URL - the part after /id/)
```

### 1.3 Export Environment Variables
Set these for easy reference in commands.
```bash
export CLUSTER_NAME="your-cluster-name"
export AWS_REGION="your-region" 
export AWS_ACCOUNT_ID="your-account-id"
export OIDC_ID="your-oidc-id"
```

### 1.4 CRITICAL: Tag AWS Resources for Karpenter Discovery
**This must be done BEFORE creating the AWSNodeTemplate, or Karpenter will fail to provision nodes.**

```bash
# Get cluster VPC resources
aws eks describe-cluster --name $CLUSTER_NAME --query 'cluster.resourcesVpcConfig.{VpcId:vpcId,SubnetIds:subnetIds,SecurityGroupIds:securityGroupIds}' --output json

# Tag subnets for discovery (replace with your actual subnet IDs)
aws ec2 create-tags --resources subnet-042f3433cd666dd57 subnet-0ece87fe94dc78aed --tags Key=karpenter.sh/discovery,Value=$CLUSTER_NAME

# Tag security group for discovery (replace with your actual security group ID) 
aws ec2 create-tags --resources sg-077e77c2cc18da300 --tags Key=karpenter.sh/discovery,Value=$CLUSTER_NAME
```

**Why this is critical:** Without these tags, Karpenter cannot discover which subnets and security groups to use for new instances, causing all provisioning to fail.

## Step 2: IAM Setup for Karpenter

Understanding: Karpenter needs 2 different IAM roles for 2 different purposes.

### 2.1 Create Karpenter Node IAM Role
**Purpose:** Used by EC2 instances that Karpenter creates
**What it needs:** Permission to join EKS cluster as worker nodes

**Step 1: Create trust policy file**
Create `node-role-trust-policy.json`:
```json
{
  "Version": "2012-10-17", 
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Step 2: Create the IAM role**
```bash
aws iam create-role \
  --role-name KarpenterNodeRole \
  --assume-role-policy-document file://$(pwd)/node-role-trust-policy.json
```

**Step 3: Attach AWS managed policies**
```bash
# Allow nodes to join EKS cluster
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

# Allow container networking
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

# Allow pulling container images
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# CRITICAL: Allow SSM parameter access for AMI discovery
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

**Step 4: Create instance profile**
```bash
# Create instance profile
aws iam create-instance-profile --instance-profile-name KarpenterNodeInstanceProfile

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name KarpenterNodeInstanceProfile \
  --role-name KarpenterNodeRole
```

**Commands to Create Node Role:**

Step 1: Create trust policy file (`node-role-trust-policy.json`):
```json
{
  "Version": "2012-10-17", 
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Step 2: Create the IAM role:
```bash
aws iam create-role \
  --role-name KarpenterNodeRole \
  --assume-role-policy-document file://$(pwd)/node-role-trust-policy.json
```

Step 3: Attach AWS managed policies:
```bash
# Allow nodes to join EKS cluster
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

# Allow container networking
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

# Allow pulling container images
aws iam attach-role-policy \
  --role-name KarpenterNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

Step 4: Create instance profile:
```bash
# Create instance profile
aws iam create-instance-profile --instance-profile-name KarpenterNodeInstanceProfile

# Add role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name KarpenterNodeInstanceProfile \
  --role-name KarpenterNodeRole
```

### 2.2 Create Karpenter Controller IAM Role
**Purpose:** Used by Karpenter controller pod to create/manage EC2 instances  
**What it needs:** Permission to call AWS APIs (create instances, describe resources, etc.)

**Step 1: Gather required information**
```bash
# Get your cluster name
kubectl config current-context

# Get AWS Account ID
aws sts get-caller-identity --query Account --output text

# Get AWS Region
aws configure get region

# Get OIDC issuer URL (replace YOUR_CLUSTER_NAME with actual name)
aws eks describe-cluster --name YOUR_CLUSTER_NAME --query cluster.identity.oidc.issuer --output text

# The OIDC_ID is the part after /id/ in the issuer URL
# Example: https://oidc.eks.ap-south-1.amazonaws.com/id/C823116DC45DCAC85D836313BD23B350
# OIDC_ID = C823116DC45DCAC85D836313BD23B350
```

**Step 2: Create trust policy file**
Create `controller-role-trust-policy.json` with your actual values:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow", 
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.REGION.amazonaws.com/id/OIDC_ID"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:sub": "system:serviceaccount:karpenter:karpenter",
        "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

**Step 3: Create custom permission policy**
Create `karpenter-controller-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateFleet",
        "ec2:CreateLaunchTemplate",
        "ec2:CreateTags",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeImages",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceTypeOfferings",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeLaunchTemplates",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSpotPriceHistory",
        "ec2:DescribeSubnets",
        "ec2:RequestSpotInstances",
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "iam:PassRole",
        "iam:CreateInstanceProfile",
        "iam:DeleteInstanceProfile",
        "iam:GetInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:RemoveRoleFromInstanceProfile",
        "eks:DescribeCluster"
      ],
      "Resource": "*"
    }
  ]
}
```

**Step 4: Create controller IAM role**
```bash
# Create the custom policy
aws iam create-policy \
  --policy-name KarpenterControllerPolicy \
  --policy-document file://$(pwd)/karpenter-controller-policy.json

# Create the IAM role
aws iam create-role \
  --role-name KarpenterControllerRole \
  --assume-role-policy-document file://$(pwd)/controller-role-trust-policy.json

# Attach the custom policy (replace ACCOUNT_ID with your actual account ID)
aws iam attach-role-policy \
  --role-name KarpenterControllerRole \
  --policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/KarpenterControllerPolicy

# CRITICAL: Attach SSM read permissions for AMI discovery
# Without this, Karpenter cannot discover EKS-optimized AMIs and will fail
aws iam attach-role-policy \
  --role-name KarpenterControllerRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### 2.3 Role Creation Order
1. **Start with Node Role** (simpler, uses AWS managed policies)  
2. **Then Controller Role** (more complex, needs custom policy)

## Step 3: Install Karpenter

### 3.1 Add Karpenter Helm Repository
```bash
helm repo add karpenter https://charts.karpenter.sh
helm repo update
```

**Check available versions:**
```bash
helm search repo karpenter --versions | head -10
```
Note: The current repository only has older versions (0.16.x). We'll use the latest available version.

### 3.2 Install Karpenter Controller

**Step 1: Get cluster endpoint**
```bash
# Get cluster endpoint (required for Karpenter)
aws eks describe-cluster --name preprod_eks_cluster --query cluster.endpoint --output text
```

**Step 2: Install Karpenter (version 0.16.3)**
```bash
# Install Karpenter with correct configuration for v0.16.3
helm install karpenter karpenter/karpenter \
  --version "0.16.3" \
  --namespace "karpenter" \
  --create-namespace \
  --set clusterName=preprod_eks_cluster \
  --set clusterEndpoint=https://799D3476CECB34B8D473026777862FC9.gr7.ap-south-1.eks.amazonaws.com \
  --set aws.defaultInstanceProfile=KarpenterNodeInstanceProfile \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/KarpenterControllerRole
```

**Important Notes:**
- Replace `ACCOUNT_ID` with your actual AWS account ID
- Replace cluster endpoint with your actual endpoint URL  
- Version 0.16.3 uses different configuration syntax than newer versions
- The serviceAccount annotation configures IRSA automatically

**If installation fails, uninstall first:**
```bash
helm uninstall karpenter -n karpenter
```

### 3.3 Verify Installation

**Check pod status:**
```bash
kubectl get pods -n karpenter
```

**Expected output:**
```
NAME                         READY   STATUS    RESTARTS   AGE
karpenter-xxxxxxxxx-xxxxx    1/2     Running   0          30s
karpenter-xxxxxxxxx-xxxxx    1/2     Running   0          30s
```

**Check controller logs:**
```bash
kubectl logs deployment/karpenter -n karpenter -c controller --tail=10
```

**Expected logs should show:**
- Server starting messages
- Leader election attempts
- No crash loop errors

**Troubleshooting:**
- If pods show `CrashLoopBackOff`, check logs for configuration errors
- If `AccessDenied` for pricing data appears, this is normal (uses cached data)
- Pods showing `1/2 Running` is normal for v0.16.3 (webhook container issue)

**Verification complete when:**
- Pods are stable in `Running` status (not crashing)
- Controller logs show successful startup
- No permission errors in logs

## Step 4: Configure IRSA for Karpenter

**Note:** If you used the Helm installation command from Step 3.2, IRSA is already configured automatically via the serviceAccount annotation. You can verify this:

### 4.1 Verify IRSA Configuration
```bash
# Check if service account has the role annotation
kubectl get serviceaccount karpenter -n karpenter -o yaml | grep role-arn
```

**Expected output:**
```
eks.amazonaws.com/role-arn: arn:aws:iam::703460697499:role/KarpenterControllerRole
```

### 4.2 Manual IRSA Configuration (if needed)
If the annotation is missing, add it manually:
```bash
kubectl annotate serviceaccount karpenter -n karpenter \
  eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT_ID:role/KarpenterControllerRole --overwrite
```

### 4.3 Restart Controller (if annotation was added manually)
```bash
kubectl rollout restart deployment karpenter -n karpenter
kubectl get pods -n karpenter
```

**Step 4 Complete:** IRSA is configured and Karpenter can assume the IAM role to manage EC2 instances.

## Step 5: Create AWSNodeTemplate

### 5.1 Create AWSNodeTemplate Resource
This tells Karpenter how to configure the EC2 instances it creates.

**Important:** For Karpenter v0.16.3, we use `AWSNodeTemplate` (not `EC2NodeClass`)

**Step 1: Create the YAML file (e.g., `ec2nodeclass.yaml`)**
```yaml
apiVersion: karpenter.k8s.aws/v1alpha1
kind: AWSNodeTemplate
metadata:
  name: default
spec:
  # Use EKS optimized AMI
  amiFamily: AL2
  
  # Use the instance profile we created
  instanceProfile: "KarpenterNodeInstanceProfile"
  
  # Security groups (use your cluster's security groups)
  securityGroupSelector:
    karpenter.sh/discovery: "YOUR_CLUSTER_NAME"
  
  # Subnets (use your cluster's private subnets)
  subnetSelector:
    karpenter.sh/discovery: "YOUR_CLUSTER_NAME"
        
  # CRITICAL: Use proper MIME format for userData in v0.16.3
  # Simple bash format will cause "malformed MIME header" errors
  userData: |
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="BOUNDARY"

    --BOUNDARY
    Content-Type: text/x-shellscript; charset="us-ascii"

    #!/bin/bash
    /etc/eks/bootstrap.sh YOUR_CLUSTER_NAME

    --BOUNDARY--
```

**Important Notes:**
- Replace `YOUR_CLUSTER_NAME` with your actual cluster name
- The MIME format userData is **required** for v0.16.3 - simple bash format will fail
- The discovery selectors will only work if you tagged the resources in Step 1.4

**Step 2: Apply the AWSNodeTemplate to the cluster**
```bash
kubectl apply -f ec2nodeclass.yaml
```

**Step 3: Verify the AWSNodeTemplate was created**
```bash
kubectl get awsnodetemplate
kubectl describe awsnodetemplate default
```

**Step 4: Verify resource tagging**
If you followed Step 1.4 correctly, you can verify the tags:
```bash
# Verify subnets are tagged
aws ec2 describe-subnets --filters "Name=tag:karpenter.sh/discovery,Values=$CLUSTER_NAME" --query 'Subnets[].{SubnetId:SubnetId,AvailabilityZone:AvailabilityZone}' --output table

# Verify security groups are tagged  
aws ec2 describe-security-groups --filters "Name=tag:karpenter.sh/discovery,Values=$CLUSTER_NAME" --query 'SecurityGroups[].{GroupId:GroupId,GroupName:GroupName}' --output table
```

If the above commands return empty results, go back to Step 1.4 and tag your resources.

**Key Differences in v0.16.3:**
- Uses `AWSNodeTemplate` instead of `EC2NodeClass`
- API version is `v1alpha1` instead of `v1beta1`
- Uses `instanceProfile` instead of `role`
- Uses `securityGroupSelector` instead of `securityGroupSelectorTerms`
- Uses `subnetSelector` instead of `subnetSelectorTerms`
- **Requires MIME format for userData**
- **Requires discovery tags on AWS resources**

## Step 6: Create Provisioner Configuration

### 6.1 Create Basic Provisioner
This defines what types of instances Karpenter can create and when to create them.

**Important:** For Karpenter v0.16.3, we use `Provisioner` (not `NodePool`)

**Step 1: Create the YAML file (e.g., `karpenter-provisioner.yaml`)**
```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: default
spec:
  # Reference the AWSNodeTemplate we created
  providerRef:
    name: default
  
  # Instance requirements
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["spot", "on-demand"]
    - key: node.kubernetes.io/instance-type
      operator: In
      values: ["t3.small", "t3.medium", "t3.large", "c5.large", "c5.xlarge"]
    - key: kubernetes.io/arch
      operator: In
      values: ["amd64"]
  
  # Set limits to control costs
  limits:
    resources:
      cpu: 1000
      memory: 1000Gi
  
  # Automatic consolidation for cost savings
  consolidation:
    enabled: true
  
  # Node properties
  labels:
    intent: apps
```

**Step 2: Apply Provisioner Configuration**
```bash
kubectl apply -f karpenter-provisioner.yaml
```

**Step 3: Verify Provisioner was created**
```bash
kubectl get provisioner
kubectl describe provisioner default
```

**Key Differences in v0.16.3:**
- Uses `Provisioner` instead of `NodePool`
- API version is `v1alpha5` instead of `v1beta1`
- Uses `providerRef` to reference `AWSNodeTemplate` (not `nodeClassRef`)
- Different consolidation syntax: `consolidation.enabled` instead of `disruption.consolidationPolicy`
- Limits wrapped in `resources:` section

**IMPORTANT: Spot Instance Permissions**
If you encounter this error during testing:
```
ERROR: AuthFailure.ServiceLinkedRoleCreationNotPermitted: The provided credentials do not have permission to create the service-linked role for EC2 Spot Instances.
```

**Immediate fix:** Modify the provisioner to use only on-demand instances:
```yaml
  requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values: ["on-demand"]  # Remove "spot" until you get proper permissions
```

Then reapply:
```bash
kubectl apply -f karpenter-provisioner.yaml
```

**Long-term solution:** Have your AWS administrator create the EC2 Spot service-linked role:
```bash
aws iam create-service-linked-role --aws-service-name spot.amazonaws.com
```

## Step 7: Testing Karpenter Functionality

### 7.1 Create Test Workload
```bash
# Create test deployment that exceeds current node capacity
cat > karpenter-test-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: karpenter-test
  namespace: default
spec:
  replicas: 4
  selector:
    matchLabels:
      app: karpenter-test
  template:
    metadata:
      labels:
        app: karpenter-test
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        resources:
          requests:
            cpu: 1000m  # 1 vCPU per pod
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 512Mi
EOF

kubectl apply -f karpenter-test-deployment.yaml
```

### 7.2 Monitor Scaling Behavior
```bash
# Check pod status (should be Pending initially)
kubectl get pods -l app=karpenter-test

# Watch Karpenter logs for provisioning activity
kubectl logs deployment/karpenter -n karpenter -c controller --follow

# Check for new nodes being created
kubectl get nodes

# Expected: Karpenter should create new nodes within 1-2 minutes
```

### 7.3 Verification and Monitoring

**Verify Node Provisioning:**
```bash
# Check that new nodes appear
kubectl get nodes

# Verify nodes have Karpenter labels
kubectl get nodes --show-labels | grep karpenter

# Check pods are scheduled on new nodes
kubectl get pods -l app=karpenter-test -o wide
```

**Clean up test:**
```bash
kubectl delete deployment karpenter-test
```

### 7.4 Monitor Costs and Test Different Instance Types
```bash
# Monitor costs by checking instance types used
kubectl get nodes --show-labels | grep karpenter

# Test different instance types by deploying workloads with different requirements
# See troubleshooting section for common test scenarios
```

## Step 8: Troubleshooting Common Issues

**Note:** If you followed all the steps above correctly, you should not encounter these issues. This section is for reference if problems arise.

### Issue 1: Karpenter Not Discovering Resources
**Error:** Pods stay pending, no nodes created
**Logs:** No provisioning activity in Karpenter logs
**Cause:** Missing discovery tags on subnets/security groups (should have been done in Step 1.4)
**Solution:** Go back to Step 1.4 and tag your resources properly

### Issue 2: SSM Parameter Access Denied
**Error:** `AccessDeniedException: not authorized to perform: ssm:GetParameter`
**Cause:** Missing SSM permissions for AMI discovery (should have been done in Step 2.2)
**Solution:** Verify the SSM policy was attached:
```bash
aws iam list-attached-role-policies --role-name KarpenterControllerRole | grep SSM
```

### Issue 3: UserData MIME Header Error  
**Error:** `malformed MIME header: missing colon: "#!/bin/bash"`
**Cause:** Wrong UserData format for v0.16.3 (should have been done correctly in Step 5.1)
**Solution:** Verify your AWSNodeTemplate uses the MIME format shown in Step 5.1

### Issue 4: Spot Instance Permission Error
**Error:** `AuthFailure.ServiceLinkedRoleCreationNotPermitted`
**Cause:** Missing permissions for EC2 Spot service-linked role (handled in Step 6.1)
**Solution:** Already covered in Step 6.1 - use on-demand instances only

### Issue 5: Nodes Created but Stay NotReady
**Cause:** UserData script issues or networking problems
**Solution:**
```bash
# Check node conditions
kubectl describe node NODE_NAME

# Check if nodes can communicate with API server
kubectl get nodes -o wide

# Verify security group allows cluster communication
```

### General Debugging Commands
```bash
# Check Karpenter controller status
kubectl get pods -n karpenter

# View Karpenter logs
kubectl logs deployment/karpenter -n karpenter -c controller

# Check AWSNodeTemplate status  
kubectl describe awsnodetemplate default

# Check Provisioner status
kubectl describe provisioner default

# List all nodes with details
kubectl get nodes -o wide --show-labels
```

## Summary: What We Fixed

By following these steps in chronological order, you avoid the 4 critical issues we encountered:

1. **Missing Discovery Tags** (Fixed in Step 1.4) - Resources tagged before AWSNodeTemplate creation
2. **Missing SSM Permissions** (Fixed in Step 2.2) - SSM policy attached during IAM role creation  
3. **Wrong UserData Format** (Fixed in Step 5.1) - MIME format used from the beginning
4. **Spot Instance Permissions** (Handled in Step 6.1) - Workaround provided upfront

## Next Steps
- Fine-tune Provisioner configurations for different workload types
- Implement production-ready monitoring and alerting
- Plan migration from existing node groups (if applicable)
- Set up cost monitoring and optimization
- Configure multiple NodePools for different workload categories