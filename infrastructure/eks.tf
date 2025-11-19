module "eks" {
 source  = "terraform-aws-modules/eks/aws"
 version = "~> 20.31"

 cluster_name    = "preprod_eks_cluster"
 cluster_version = "1.31"

 # Optional
 cluster_endpoint_public_access = true

 # Optional: Adds the current caller identity as an administrator via cluster access entry
 enable_cluster_creator_admin_permissions = true

 # Increase timeouts for EKS cluster operations
 cluster_timeouts = {
   create = "30m"
   update = "30m" 
   delete = "30m"
 }

 eks_managed_node_groups = {
   example = {
     instance_types = ["t3.medium"]
     min_size       = 1
     max_size       = 3
     desired_size   = 2
     
     # Node group specific timeouts
     timeouts = {
       create = "30m"
       update = "30m"
       delete = "30m"
     }
   }
 }

 vpc_id     = aws_vpc.main.id
 subnet_ids = aws_subnet.public_subnet.*.id

 tags = {
   Environment = "dev"
   Terraform   = "true"
 }
}
