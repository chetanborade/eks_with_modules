# Kubernetes Karpenter Learning Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [The Problem Space](#the-problem-space)
4. [Karpenter Architecture](#karpenter-architecture)
5. [Karpenter vs Cluster Autoscaler](#karpenter-vs-cluster-autoscaler)
6. [Q&A Session](#qa-session)

---

## Introduction

This document captures a comprehensive learning session about Kubernetes Karpenter, an advanced autoscaling solution for Kubernetes clusters. The goal is to understand Karpenter from scratch, including its architecture, benefits, and how it differs from traditional autoscaling approaches.

**Target Audience:** SREs and DevOps engineers looking to understand and implement Karpenter

**Date:** December 2024

---

## Prerequisites

Before diving into Karpenter, you should understand:

- Kubernetes scheduling fundamentals
- Pod lifecycle and scheduling constraints
- Cloud provider infrastructure (AWS ASGs, GCP MIGs, etc.)
- Traditional Cluster Autoscaler concepts

---

## The Problem Space

### Why Do We Need Autoscaling?

In Kubernetes, when you deploy pods that can't be scheduled because there aren't enough node resources, you need a way to automatically add more nodes to your cluster.

### When Pods Can't Be Scheduled

**Main reasons for unschedulable pods:**

1. **Insufficient Resources**
   - Not enough CPU
   - Not enough memory
   - Missing specialized resources (GPU, ephemeral storage)

2. **Scheduling Constraints**
   - Taints and tolerations mismatch
   - Node affinity rules not satisfied
   - Pod affinity/anti-affinity rules
   - Node selectors not matching

3. **PersistentVolume Constraints**
   - Volume only available in certain zones
   - Volume already attached to another node

4. **Topology Spread Constraints**
   - Rules about pod distribution across nodes/zones not satisfied

5. **Resource Quotas**
   - Namespace-level limits preventing scheduling

### How Kubernetes Scheduler Works

The Kubernetes scheduler makes placement decisions by:
1. Filtering nodes (removing nodes that don't meet requirements)
2. Scoring remaining nodes (ranking based on best fit)
3. Selecting the highest-scored node
4. If no node fits → pod remains in "Pending" state

---

## Traditional Approach: Cluster Autoscaler

### Node Groups/Node Pools

**What are they?**
Node groups (AWS Auto Scaling Groups, GCP Managed Instance Groups) are templates that define:
- Instance type/size
- AMI/image
- Disk configuration
- Network settings
- Labels and taints
- IAM roles/service accounts

**How Cluster Autoscaler Works:**

```
1. Pod becomes pending (unschedulable)
2. Cluster Autoscaler checks on polling cycle (periodic, not immediate)
3. CA analyzes which pre-defined node group could fit the pod
4. CA calls ASG/MIG API to increase desired count
5. Cloud provider launches instance from launch template
6. Node joins cluster via kubelet
7. Pod gets scheduled
```

**Limitations:**
- Must pre-define node groups
- Limited flexibility in instance type selection
- Slower provisioning (goes through ASG layer)
- Manual tuning required for different workload types
- Can lead to resource waste (over-provisioning)

---

---

## Understanding CRDs (Custom Resource Definitions)

### What Are CRDs?

**Important:** CRDs are NOT pods! They're different concepts.

**CRD = Custom Resource Definition**
- A way to extend Kubernetes API with new resource types
- Like creating a blueprint or schema
- Defines what fields/validation a new resource type can have

**CR = Custom Resource**
- An instance of a CRD
- Just configuration/data stored in etcd
- NOT a running process or pod

**Controller Pod**
- A regular pod that watches and acts on custom resources
- Reads CRs and performs actions based on them

### Analogy

**Built-in Kubernetes resources:**
- Pod, Service, Deployment, ConfigMap (these exist by default)

**CRDs let you create NEW resource types:**
- NodePool (Karpenter)
- Certificate (cert-manager)
- VirtualService (Istio)

### How It Works with Karpenter

```
┌─────────────────────────────────────────────────────┐
│          Kubernetes Cluster                         │
│                                                      │
│  ┌────────────────────────────────┐                │
│  │   Karpenter Controller         │                │
│  │   (This IS a Pod)              │                │
│  │                                 │                │
│  │   - Watches NodePool CRs       │                │
│  │   - Watches pending pods       │                │
│  │   - Provisions EC2 instances   │                │
│  └────────────────────────────────┘                │
│           ↑ reads                                   │
│           │                                         │
│  ┌────────┴───────────────────────┐                │
│  │   NodePool Custom Resource     │                │
│  │   (This is NOT a Pod)          │                │
│  │   (It's configuration data)    │                │
│  │                                 │                │
│  │   kind: NodePool                │                │
│  │   spec:                         │                │
│  │     requirements: [...]         │                │
│  │     limits: {...}               │                │
│  └─────────────────────────────────┘                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Installation Process

**Step 1: Install CRD (the definition)**
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nodepools.karpenter.sh
spec:
  # Defines what a "NodePool" looks like
  # What fields are allowed, types, validation
```
This teaches Kubernetes: "NodePool is now a valid resource type"

**Step 2: Deploy Karpenter controller pod**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: karpenter
spec:
  template:
    spec:
      containers:
      - name: karpenter
        image: public.ecr.aws/karpenter/controller:latest
```
This is the actual running process that watches NodePools

**Step 3: Create NodePool instances**
```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool  # Now valid because CRD was installed
metadata:
  name: default
spec:
  requirements: [...]
```
This is configuration data that Karpenter controller reads

### Comparison: Built-in vs Custom Resources

**Built-in Resource (Deployment):**
```yaml
apiVersion: apps/v1
kind: Deployment  # Built-in, always available
metadata:
  name: nginx
spec:
  replicas: 3
```
→ kube-controller-manager (built-in) watches and creates Pods

**Custom Resource (NodePool):**
```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool  # Custom, must install CRD first
metadata:
  name: default
spec:
  limits:
    cpu: 100
```
→ Karpenter controller pod (you install it) watches and provisions nodes

### Key Takeaways

1. **CRD** = Schema definition (installed once)
2. **CR** = Configuration instance (not a pod, just data)
3. **Controller Pod** = Process that reads CRs and acts on them
4. When you `kubectl apply -f nodepool.yaml`:
   - NodePool CR gets stored in etcd
   - Karpenter controller pod sees the change
   - Controller reads the config and acts accordingly

---

## Karpenter Architecture

### Core Components

#### 1. Karpenter Controller
A Kubernetes deployment running in your cluster that continuously watches for:
- Unschedulable pods (via Kubernetes scheduler events)
- Node utilization metrics
- Consolidation opportunities (cost optimization)
- Disruption events (spot terminations, node expiry)

#### 2. Provisioner/NodePool (CRD)
Custom Resource Definition that defines autoscaling configuration:

**Key fields:**
- **Requirements:** Instance types, families, architectures, zones allowed
- **Resource Limits:** Max CPU/memory to control costs
- **Taints:** Taints to apply to provisioned nodes
- **Labels:** Labels to add to nodes
- **TTL/Expiration:** Time-to-live for nodes (for security updates)
- **Consolidation:** Enable/disable cost optimization
- **Disruption Budget:** Control disruption rate

**Note:** v1beta1 uses "NodePool" and "EC2NodeClass" instead of "Provisioner"

#### 3. Cloud Provider Integration
Direct API integration with cloud providers:
- AWS EC2 API
- Azure Compute API  
- GCP Compute Engine API

**No intermediate layer** - Karpenter calls these APIs directly.

### How Karpenter Works (Step-by-Step)

```
1. Pod becomes unschedulable
   ↓
2. Kubernetes scheduler marks pod as Pending with reason
   ↓
3. Karpenter controller IMMEDIATELY sees this event (watch-based, not polling)
   ↓
4. Karpenter analyzes pod requirements:
   - CPU requests
   - Memory requests
   - Node selectors
   - Affinity/anti-affinity rules
   - Tolerations
   - Topology constraints
   ↓
5. Karpenter calculates optimal instance type(s) from allowed options
   ↓
6. **KEY STEP:** Karpenter directly calls cloud provider API
   Example: EC2 RunInstances with specific instance type
   ↓
7. Instance launches and joins cluster
   ↓
8. Pod gets scheduled (typically within 30-60 seconds)
```

### Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                          │
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Pending    │         │  Karpenter   │                      │
│  │     Pod      │         │  Controller  │                      │
│  │  (CPU: 2)    │         │   (Pod)      │                      │
│  │  (Mem: 4Gi)  │         │              │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                               │
│         │ 1. Can't schedule      │                               │
│         │    (no node fits)      │                               │
│         └───────────────────────►│                               │
│                                  │                               │
│                                  │ 2. Watch event received       │
│                                  │    (immediate notification)   │
│                                  │                               │
│         ┌────────────────────────┘                               │
│         │ 3. Analyze requirements:                               │
│         │    - CPU: 2 cores                                      │
│         │    - Memory: 4Gi                                       │
│         │    - Zone: us-east-1a                                  │
│         │    - Arch: amd64                                       │
│         │                                                         │
│         │ 4. Check NodePool constraints:                         │
│  ┌──────▼────────────┐                                           │
│  │    NodePool CRD   │                                           │
│  │  ─────────────    │                                           │
│  │  requirements:    │                                           │
│  │   - instance:     │                                           │
│  │     [t3, t3a, c5] │                                           │
│  │   - arch: amd64   │                                           │
│  │   - capacity:     │                                           │
│  │     spot/on-demand│                                           │
│  └───────────────────┘                                           │
│         │                                                         │
│         │ 5. Calculate best fit:                                 │
│         │    → t3.large (2 vCPU, 8GB) ✓                         │
│         │                                                         │
└─────────┼─────────────────────────────────────────────────────────┘
          │
          │ 6. Direct API call (NO ASG!)
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AWS EC2 API                              │
│                                                                   │
│                    RunInstances()                                │
│                    ─────────────                                 │
│                    InstanceType: t3.large                        │
│                    AMI: ami-xxxxx                                │
│                    SecurityGroups: [sg-xxxxx]                    │
│                    IAMInstanceProfile: KarpenterNodeRole         │
│                    UserData: <kubelet bootstrap>                 │
│                                                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ 7. EC2 instance launched
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      New EC2 Instance                            │
│                                                                   │
│  ┌────────────────────────────────────────────┐                 │
│  │  Kubelet starts and registers with K8s     │                 │
│  │  Node becomes Ready                        │                 │
│  └────────────────────────────────────────────┘                 │
│                                                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ 8. Node joins cluster
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                          │
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Pending    │         │   New Node   │                      │
│  │     Pod      │────────►│  (t3.large)  │                      │
│  │              │ Scheduled│   Ready      │                      │
│  └──────────────┘         └──────────────┘                      │
│                                                                   │
│  Total time: ~30-60 seconds                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Comparison: Cluster Autoscaler vs Karpenter Flow

**Cluster Autoscaler Flow:**
```
Pending Pod → CA polls (every 10s) → Picks ASG → Calls ASG API 
→ ASG updates desired count → ASG calls EC2 API → Instance launches 
→ Joins cluster → Pod scheduled
Time: 3-5 minutes
```

**Karpenter Flow:**
```
Pending Pod → Immediate watch event → Calculates instance type 
→ Direct EC2 API call → Instance launches → Joins cluster 
→ Pod scheduled
Time: 30-60 seconds
```

**Key Differences:**
1. **No polling delay** - Karpenter uses Kubernetes watch API
2. **No ASG layer** - Direct EC2 API calls
3. **No pre-defined groups** - Dynamic instance selection
4. **Faster decision making** - Real-time pod requirement analysis

### Key Architectural Advantages

1. **No Node Groups Required:** Provisions nodes on-demand
2. **Event-Driven:** Uses Kubernetes watch API (immediate reaction)
3. **Direct Provisioning:** Bypasses ASG/MIG layer
4. **Bin-Packing Optimization:** Smart instance type selection
5. **Consolidation:** Automatically replaces nodes with cheaper/smaller options

---

## Karpenter vs Cluster Autoscaler

### How They Run

**Cluster Autoscaler:**
- Runs as a **Deployment** (regular pod) in your cluster, typically in `kube-system` namespace
- Does **NOT** use CRDs for configuration
- Configuration via:
  - Command-line flags/arguments in the deployment
  - ConfigMap (in some setups)
  - Cloud provider-specific annotations on node groups

**Example Cluster Autoscaler configuration:**
```yaml
# Configuration via deployment args
args:
  - --cloud-provider=aws
  - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled
  - --balance-similar-node-groups
  - --skip-nodes-with-system-pods=false
```

**Karpenter:**
- Also runs as a **Deployment** in your cluster
- **Uses CRDs** (Custom Resource Definitions) for configuration:
  - `Provisioner` (v1alpha5) or `NodePool` (v1beta1+)
  - `AWSNodeTemplate` or `EC2NodeClass` (for AWS-specific settings)

**Example Karpenter configuration:**
```yaml
# Configuration via CRD
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
```

### Why Karpenter Uses CRDs

**Advantages of CRDs over command-line arguments:**

1. **Multiple Configurations:** Create multiple NodePools with different rules
   - Example: Separate NodePools for general workloads, GPU workloads, spot instances
   - CLI args limit you to single global configuration

2. **Dynamic Updates:** Modify CRDs without restarting the Karpenter controller
   - CLI args require pod restart for changes

3. **Kubernetes-Native:** CRDs are first-class Kubernetes objects
   - Manage with `kubectl`
   - Version control with GitOps (ArgoCD, Flux)
   - Apply RBAC permissions
   - Audit changes through Kubernetes API

4. **Declarative:** Fits Kubernetes declarative model
   - Declare desired state, Karpenter reconciles

5. **Flexibility:** Each NodePool can target specific workloads
   - Pod selectors
   - Node selectors
   - Taints and tolerations
   - Different instance type constraints per workload

### Comparison Table

| Aspect | Cluster Autoscaler | Karpenter |
|--------|-------------------|-----------|
| **Deployment** | Pod in kube-system | Pod in cluster |
| **Configuration** | CLI args, ConfigMap | CRDs (NodePool, EC2NodeClass) |
| **Node Groups** | Required (pre-defined) | Not required |
| **Provisioning Speed** | Minutes (via ASG) | Seconds (direct API) |
| **Instance Selection** | Limited to pre-defined groups | Dynamic from allowed types |
| **Detection Method** | Polling-based | Event-driven (watch) |
| **Consolidation** | Manual/limited | Automatic built-in |
| **Multi-Architecture** | Separate node groups | Single provisioner |
| **Spot Integration** | Complex setup | Native support |
| **Multi-Configuration** | Single global config | Multiple NodePools possible |

### Why Karpenter is Faster

**Architectural Difference:**

**Cluster Autoscaler:**
```
Pod Pending → CA polls → Picks node group → ASG API → 
Launch template → Instance launch → Join cluster
(Multiple layers, ~3-5 minutes)
```

**Karpenter:**
```
Pod Pending → Immediate event → Calculate optimal instance → 
EC2 RunInstances → Instance launch → Join cluster
(Direct path, ~30-60 seconds)
```

**Speed improvement comes from:**
1. Event-driven vs polling
2. No ASG middle layer
3. Pre-calculated optimal instance types
4. Parallel provisioning of multiple instance types

---

## Q&A Session

### Q1: When a pod can't be scheduled, what are the main reasons?

**Answer:** 
- Node resources are full (CPU, memory, storage)
- Nodes have taints that the pod doesn't tolerate
- Node affinity/selector conditions not met
- Volume availability constraints
- Topology spread constraints

### Q2: How do node groups work?

**Answer:**
Node groups are templates that define how nodes should be configured. Based on the node group's configuration (instance type, AMI, labels, taints), identical nodes are provisioned when scaling is needed.

### Q3: Why can Karpenter provision nodes faster than Cluster Autoscaler?

**Answer:**
Karpenter bypasses the Auto Scaling Group (ASG) layer and directly calls the cloud provider API (e.g., EC2 RunInstances). It's also event-driven rather than polling-based, so it reacts immediately to unschedulable pods. Cluster Autoscaler must go through: polling → ASG API → launch template → instance launch, adding significant latency.

### Q4: Are there workloads where pre-defined node groups might be preferable to Karpenter?

**Discussion Point:** While Karpenter benefits most workloads, consider:
- **Compliance requirements:** Some organizations require pre-approved instance types
- **Predictable costs:** Pre-defined groups offer more predictable billing
- **Specific kernel/AMI requirements:** Need strict control over base images
- **Stateful workloads:** Where node churn could be disruptive
- **Reserved Instances/Savings Plans:** Already committed to specific instance types

However, Karpenter can address most of these with proper configuration!

### Q5: Does Cluster Autoscaler run as a CRD pod on Kubernetes like Karpenter?

**Answer:**
Both run as Deployment pods, but configuration differs:

**Cluster Autoscaler:**
- Runs as regular Deployment in `kube-system`
- Configured via CLI arguments and ConfigMaps
- No CRDs involved in configuration
- Single global configuration

**Karpenter:**
- Runs as Deployment in cluster
- Uses CRDs for configuration (NodePool, EC2NodeClass)
- Allows multiple configurations
- Kubernetes-native declarative approach

### Q6: Why does Karpenter use CRDs instead of command-line arguments?

**Answer:**
1. **Multiple Configurations:** Can have different NodePools for different workload types
2. **Dynamic Updates:** Change configuration without pod restart
3. **Kubernetes-Native:** Use kubectl, GitOps, RBAC, audit trails
4. **Declarative:** Fits Kubernetes model
5. **Flexibility:** Target specific workloads with different rules

### Q7: Can you explain the complete Karpenter flow? Does it call EKS API or AWS API?

**Answer:**
Karpenter flow summary:
1. Karpenter runs as a pod in the cluster
2. Uses CRDs (NodePool) for configuration
3. Watches for unscheduled pods (event-driven)
4. Analyzes pod requirements (CPU, memory, labels, taints, etc.)
5. **Calls EC2 API directly** (NOT EKS API) to launch instances
6. Instance joins cluster via kubelet
7. Pod gets scheduled

**Important clarification:** 
- Karpenter calls **EC2 API** (e.g., `RunInstances`), not EKS API
- EKS is just the Kubernetes control plane
- The actual compute nodes are EC2 instances
- Karpenter provisions EC2 instances directly, bypassing Auto Scaling Groups

**Total time:** ~30-60 seconds (vs 3-5 minutes with Cluster Autoscaler)

### Q8: Which step in the Karpenter flow is most time-consuming?

**Answer:** EC2 instance launch and cluster join (~20-40 seconds)

**Timing breakdown:**
1. Karpenter watches/analyzes: ~milliseconds (in-memory operations)
2. EC2 API call: ~1-2 seconds (network + API processing)
3. **EC2 instance launch: ~20-40 seconds (BOTTLENECK)**
   - Boot OS
   - Run user data scripts
   - Initialize networking
4. Kubelet registration: ~5-10 seconds
   - Kubelet starts
   - Registers with K8s API
   - Node becomes "Ready"
5. Pod scheduling: ~1-2 seconds

**Key insight:** You can't eliminate EC2 boot time - physical infrastructure needs time to start. This is why even Karpenter takes 30-60 seconds total.

### Q9: How does Karpenter handle multiple pending pods efficiently?

**Answer:** Batch provisioning and bin-packing

When multiple pods become pending simultaneously, Karpenter:

1. **Batches the analysis** - Analyzes all pending pods together (not one-by-one)
2. **Bin-packing algorithm** - Calculates optimal node sizes to fit multiple pods
3. **Provisions efficiently** - Launches fewer, appropriately-sized nodes

**Example scenario:**
- 10 pods pending, each needs: 0.5 CPU, 1GB RAM
- **Inefficient approach:** Launch 10 x t3.small instances
- **Karpenter approach:** Launch 2 x t3.large instances (fits 5 pods each)
- **Benefits:** Fewer nodes, lower cost, less overhead, faster provisioning

This is called **consolidation-aware provisioning** - one of Karpenter's key advantages.

### Q10: What are CRDs? Are they pods?

**Answer:** No, CRDs are NOT pods. They're completely different concepts.

**CRD (Custom Resource Definition):**
- A schema/blueprint that defines a new Kubernetes resource type
- Extends the Kubernetes API
- Installed once (usually by Helm/operator)
- Example: Defines what a "NodePool" resource looks like

**CR (Custom Resource):**
- An instance of a CRD
- Just configuration data stored in etcd
- NOT a running process or pod
- Example: A specific NodePool configuration

**Controller Pod:**
- A regular pod that watches custom resources
- Reads CRs and performs actions
- Example: Karpenter controller pod watches NodePool CRs

**The relationship:**
1. Install CRD → Kubernetes now knows "NodePool" is valid
2. Deploy Karpenter controller pod → Running process that watches NodePools
3. Create NodePool CR → Configuration that controller reads and acts on

**Analogy:** 
- CRD = Blueprint for a house
- CR = Specific house design you create
- Controller = Builder who reads the design and builds it

### Q11: Simplified understanding - CRD, CR, and Controller relationship?

**Answer (Student's Summary):**

**CRD → Blueprint**
**CR → Instance of the blueprint**
**Controller → Does what the CR mentions**

**Concrete example:**

```
CRD (Blueprint):
"A NodePool must have: requirements, limits, disruption settings"

CR (Instance):
NodePool named "default" with:
- requirements: t3 instances, amd64 arch
- limits: 100 CPU max
- disruption: consolidate when underutilized

Controller (Action):
Karpenter pod reads this CR and:
- Only provisions t3, amd64 instances
- Never exceeds 100 CPUs total
- Replaces nodes to save money when underutilized
```

**Multiple CRs from same CRD:**
```
CRD: NodePool (blueprint - installed once)
  ↓
CR #1: NodePool "general-purpose" (t3 instances)
CR #2: NodePool "gpu-workloads" (p3 instances with GPU)
CR #3: NodePool "batch-jobs" (spot instances only)
```

The same Karpenter controller pod reads all three and handles each differently!

*To be continued as learning progresses...*

---

## Next Topics to Cover

- [ ] Karpenter configuration deep-dive (Provisioner/NodePool specs)
- [ ] NodeClass and launch templates
- [ ] Consolidation strategies
- [ ] Spot instance integration
- [ ] Disruption budgets
- [ ] Cost optimization patterns
- [ ] Multi-tenancy considerations
- [ ] Migration from Cluster Autoscaler
- [ ] Monitoring and observability
- [ ] Troubleshooting common issues

---

## Resources

- [Official Karpenter Documentation](https://karpenter.sh/)
- [Karpenter GitHub Repository](https://github.com/aws/karpenter)
- [AWS Karpenter Best Practices](https://aws.github.io/aws-eks-best-practices/karpenter/)

---

*This is a living document. Last updated: December 2024*
