# Complete EKS EBS CSI Driver and Velero Backup Setup Guide

**Goal**: Set up EKS cluster with EBS persistent storage and Velero backup solution that backs up both Kubernetes manifests to S3 and EBS volume snapshots.

## Prerequisites
- EKS cluster running (via Terraform or eksctl)
- AWS CLI configured with admin permissions
- kubectl configured to access your cluster
- Basic understanding of Kubernetes

---

## Part 1: EBS CSI Driver Setup with IRSA

### Step 1: Create EBS CSI Trust Policy
Create `infrastructure/ebs_trust_policy.json`:
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
        "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa",
        "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

**CRITICAL**: Replace `ACCOUNT_ID`, `REGION`, and `OIDC_ID` with your actual values. Do NOT include `https://` in the Condition section.

### Step 1.5: Clean Up Existing Roles (if they exist)
Before creating new roles with updated trust policies, check and clean up any existing roles:

```bash
# Check if EBS CSI role exists
aws iam get-role --role-name ebs-csi-role
# If it exists, delete it:
# aws iam detach-role-policy --role-name ebs-csi-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
# aws iam delete-role --role-name ebs-csi-role

# Check if Velero role exists and what policies are attached
aws iam get-role --role-name velero-role
aws iam list-attached-role-policies --role-name velero-role
# If it exists, delete it and its custom policies:
# aws iam detach-role-policy --role-name velero-role --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/[ACTUAL_POLICY_NAME]
# aws iam delete-role --role-name velero-role
# 
# Delete policy versions if multiple exist:
# aws iam list-policy-versions --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/[ACTUAL_POLICY_NAME]
# aws iam delete-policy-version --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/[ACTUAL_POLICY_NAME] --version-id v2
# aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/[ACTUAL_POLICY_NAME]
```

### Step 2: Create EBS CSI IAM Role
```bash
# Create role using absolute path
aws iam create-role \
  --role-name ebs-csi-role \
  --assume-role-policy-document file://$(pwd)/infrastructure/ebs_trust_policy.json

# Attach AWS managed policy (recommended)
aws iam attach-role-policy \
  --role-name ebs-csi-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy

# Verify policy attached
aws iam list-attached-role-policies --role-name ebs-csi-role
```



### Step 3: Install EBS CSI Driver Add-on
```bash
# Install the add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name aws-ebs-csi-driver

# Wait for installation (takes 2-3 minutes)
kubectl get pods -n kube-system | grep ebs
# Wait until you see ebs-csi-controller and ebs-csi-node pods
```

### Step 4: Configure IRSA for EBS CSI
```bash
# Annotate service account
kubectl annotate serviceaccount ebs-csi-controller-sa -n kube-system \
  "eks.amazonaws.com/role-arn=arn:aws:iam::$ACCOUNT_ID:role/ebs-csi-role" --overwrite

# Restart deployment
kubectl rollout restart deployment ebs-csi-controller -n kube-system

# Verify pods are running (this may take 60-90 seconds)
kubectl get pods -n kube-system -l app=ebs-csi-controller
```

**Expected output**: 2 pods showing `6/6 Running`

### Step 5: Test EBS CSI with nginx Application

Create namespace:
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: velero-test
EOF
```

Create PVC:
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nginx-storage
  namespace: velero-test
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: gp2
EOF
```

Create nginx deployment and service:
```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-app
  namespace: velero-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: storage
          mountPath: /usr/share/nginx/html
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: nginx-storage
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: velero-test
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
EOF
```

Verify nginx is working:
```bash
# Check pods and PVC
kubectl get pods -n velero-test
kubectl get pvc -n velero-test

# Both should show Running/Bound status
# Add custom content to test persistence
kubectl exec deployment/nginx-app -n velero-test -- sh -c "echo '<h1>Welcome to Velero POC!</h1><p>This data is stored on EBS volume</p>' > /usr/share/nginx/html/index.html"

# Test via LoadBalancer (get external IP first)
kubectl get svc -n velero-test
# curl <EXTERNAL-IP> should show your custom content
```

---

## Part 2: Velero Backup Setup

### Step 6: S3 Bucket (Already created by Terraform)
```bash
# Bucket was already created by Terraform during cluster creation
echo "S3 bucket: $BUCKET_NAME"
aws s3 ls s3://$BUCKET_NAME
# Should show empty bucket ready for Velero backups
```

### Step 7: Create Velero IAM Policy
Create `infrastructure/velero-complete-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::BUCKET_NAME",
        "arn:aws:s3:::BUCKET_NAME/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeSnapshots",
        "ec2:CreateSnapshot",
        "ec2:DeleteSnapshot",
        "ec2:DescribeInstances",
        "ec2:CreateTags",
        "ec2:DescribeImages",
        "ec2:DescribeInstanceAttribute",
        "ec2:ModifySnapshotAttribute"
      ],
      "Resource": "*"
    }
  ]
}
```

**IMPORTANT**: Replace `BUCKET_NAME` with your actual bucket name from Step 7.

Create policy:
```bash
aws iam create-policy \
  --policy-name velero-complete-policy \
  --policy-document file://$(pwd)/infrastructure/velero-complete-policy.json
```

### Step 8: Create Velero Trust Policy
Create `infrastructure/velero_trust_policy.json`:
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
        "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:sub": "system:serviceaccount:velero:velero",
        "oidc.eks.REGION.amazonaws.com/id/OIDC_ID:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

**CRITICAL**: Replace `ACCOUNT_ID`, `REGION`, and `OIDC_ID` with your actual values. Note the different namespace (`velero`) and service account (`velero`).

### Step 9: Create Velero IAM Role
```bash
# Create role
aws iam create-role \
  --role-name velero-role \
  --assume-role-policy-document file://$(pwd)/infrastructure/velero_trust_policy.json

# Attach policy
aws iam attach-role-policy \
  --role-name velero-role \
  --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/velero-complete-policy

# Verify
aws iam list-attached-role-policies --role-name velero-role
```

### Step 10: Install Velero
Download Velero CLI:
```bash
# For Mac
curl -LO https://github.com/vmware-tanzu/velero/releases/download/v1.12.1/velero-v1.12.1-darwin-amd64.tar.gz
tar -xzf velero-v1.12.1-darwin-amd64.tar.gz

# For Linux
curl -LO https://github.com/vmware-tanzu/velero/releases/download/v1.12.1/velero-v1.12.1-linux-amd64.tar.gz
tar -xzf velero-v1.12.1-linux-amd64.tar.gz
```

Install Velero on cluster:
```bash
# Use the correct binary path for your OS
./velero-v1.12.1-darwin-amd64/velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket $BUCKET_NAME \
  --backup-location-config region=$AWS_REGION \
  --snapshot-location-config region=$AWS_REGION \
  --no-secret

# Verify installation
kubectl get pods -n velero
# Should show velero pod Running
```

### Step 11: Configure IRSA for Velero
```bash
# Annotate Velero service account
kubectl annotate serviceaccount velero -n velero \
  "eks.amazonaws.com/role-arn=arn:aws:iam::$ACCOUNT_ID:role/velero-role" --overwrite

# Restart Velero
kubectl rollout restart deployment velero -n velero

# Verify
kubectl get pods -n velero
kubectl get sa velero -n velero -o yaml | grep role-arn
```

---

## Part 3: Complete Backup and Verification

### Step 12: Create Complete Backup
```bash
# Create backup with EBS snapshots
./velero-v1.12.1-darwin-amd64/velero backup create nginx-complete-backup \
  --selector app=nginx \
  --snapshot-volumes=true

# Check backup status
./velero-v1.12.1-darwin-amd64/velero backup describe nginx-complete-backup
```

**Expected output**: `Phase: Completed` and `Velero-Native Snapshots: 1 of 1 snapshots completed successfully`

### Step 13: Verify Complete Backup
Check S3 backup:
```bash
aws s3 ls s3://$BUCKET_NAME/backups/ --recursive
# Should show backup files
```

Check EBS snapshot:
```bash
aws ec2 describe-snapshots --owner-ids self \
  --filters "Name=tag:velero.io/backup,Values=nginx-complete-backup" \
  --query 'Snapshots[].{ID:SnapshotId,State:State,Progress:Progress}' --output table
# Should show completed snapshot
```

### Step 14: Test Application Access
```bash
# Get LoadBalancer URL
kubectl get svc nginx-service -n velero-test
# Test the application
curl <EXTERNAL-IP>
# Should return: "Welcome to Velero POC! This data is stored on EBS volume"
```

---

## Troubleshooting Guide

### EBS CSI Driver Issues

**Problem**: EBS CSI pods CrashLoopBackOff with `ec2:DescribeAvailabilityZones not authorized`

**Solutions**:
1. **Verify OIDC ID matches in trust policy**:
   ```bash
   aws eks describe-cluster --name $CLUSTER_NAME --query 'cluster.identity.oidc.issuer'
   cat infrastructure/ebs_trust_policy.json | grep oidc-provider
   # IDs must match exactly
   ```

2. **Check service account annotation**:
   ```bash
   kubectl get sa ebs-csi-controller-sa -n kube-system -o yaml | grep role-arn
   ```

3. **Force pod restart**:
   ```bash
   kubectl delete pods -l app=ebs-csi-controller -n kube-system
   sleep 30
   kubectl get pods -n kube-system | grep ebs
   ```

### Velero Backup Issues

**Problem**: Backup fails with S3 access denied

**Solutions**:
1. **Verify bucket name in policy**:
   ```bash
   cat infrastructure/velero-complete-policy.json | grep s3
   # Must match actual bucket name
   ```

2. **Check EC2 permissions for EBS snapshots**:
   ```bash
   aws iam get-policy-version --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/velero-complete-policy --version-id v1
   # Should include ec2:DescribeVolumes, ec2:CreateSnapshot, etc.
   ```

### File Path Issues
- Always use absolute paths: `file://$(pwd)/infrastructure/filename.json`
- Ensure files exist: `ls -la infrastructure/`

### Permission Verification Script
```bash
#!/bin/bash
echo "=== EKS Backup Setup Verification ==="
echo "1. EBS CSI Status:"
kubectl get pods -n kube-system | grep ebs
echo "2. Nginx App Status:"
kubectl get pods -n velero-test
kubectl get pvc -n velero-test
echo "3. Velero Status:"
kubectl get pods -n velero
echo "4. IAM Roles:"
aws iam list-attached-role-policies --role-name ebs-csi-role
aws iam list-attached-role-policies --role-name velero-role
echo "5. Recent Backups:"
./velero-v1.12.1-darwin-amd64/velero backup get
```

## Success Criteria

✅ **EBS CSI**: 2 pods showing `6/6 Running`  
✅ **nginx app**: Pod `1/1 Running`, PVC `Bound`  
✅ **Velero**: Pod `1/1 Running`  
✅ **Backup**: Status `Completed` with EBS snapshot  
✅ **Application accessible**: LoadBalancer returns custom content  

## File Structure
```
velero-poc/
├── infrastructure/
│   ├── ebs_trust_policy.json
│   ├── velero_trust_policy.json
│   └── velero-complete-policy.json
├── velero-v1.12.1-darwin-amd64/
└── STEPS.md
```

## Environment Variables Summary
```bash
# All values come from Terraform outputs
cd /Users/one2n/Desktop/eks_with_modules/infrastructure
export CLUSTER_NAME=$(terraform output -raw cluster_name)
export OIDC_ID=$(terraform output -raw oidc_id)
export AWS_REGION=$(terraform output -raw aws_region)
export ACCOUNT_ID=$(terraform output -raw account_id)
export BUCKET_NAME=$(terraform output -raw velero_bucket_name)
```

## Clean Up (Before terraform destroy)

**IMPORTANT**: Before running `terraform destroy`, you must clean up resources created outside Terraform:

### Step 1: Delete Velero Backups and EBS Snapshots
```bash
# Navigate to Velero directory
cd /Users/one2n/Desktop/eks_with_modules/velero-poc

# Delete ALL backups (this also deletes associated EBS snapshots)
./velero-v1.12.1-darwin-amd64/velero backup delete --all --confirm

# Verify all backups are deleted
./velero-v1.12.1-darwin-amd64/velero backup get

# Check that EBS snapshots are also deleted
aws ec2 describe-snapshots --owner-ids self --filters "Name=tag:velero.io/backup,Values=*"
```

### Step 2: Clean up Kubernetes Resources
```bash
# Delete test application
kubectl delete namespace velero-test

# Delete Velero (optional - will be deleted by terraform destroy anyway)
kubectl delete namespace velero
```

### Step 3: Delete IAM Roles and Policies
```bash
# Set environment variables if not already set
cd /Users/one2n/Desktop/eks_with_modules/infrastructure
export ACCOUNT_ID=$(terraform output -raw account_id)

# Delete IAM resources
aws iam detach-role-policy --role-name ebs-csi-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
aws iam delete-role --role-name ebs-csi-role
aws iam detach-role-policy --role-name velero-role --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/velero-complete-policy
aws iam delete-role --role-name velero-role
aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/velero-complete-policy
```

### Step 4: Terraform Destroy
```bash
# Now safe to destroy Terraform resources (including S3 bucket)
cd /Users/one2n/Desktop/eks_with_modules/infrastructure
terraform destroy
```

**Why this order matters:**
- EBS snapshots created by Velero won't be deleted by `terraform destroy`
- S3 bucket must be empty before Terraform can delete it
- IAM roles/policies were created manually, not by Terraform

---

**This guide provides complete instructions for setting up EKS with EBS CSI driver and Velero backup solution. Follow each step carefully and use the troubleshooting section if you encounter issues.**