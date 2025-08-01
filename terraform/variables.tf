# Terraform Variables for Nautilus Trader Infrastructure

# General Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "nautilus-trader"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "nautilus-trader-team"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "nautilus-trader.com"
}

# Terraform State Configuration
variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  type        = string
  default     = "nautilus-trader-terraform-state"
}

variable "terraform_lock_table" {
  description = "DynamoDB table for Terraform state locking"
  type        = string
  default     = "nautilus-trader-terraform-locks"
}

# Kubernetes Configuration
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS node group"
  type        = list(string)
  default     = ["m5.large", "m5.xlarge"]
}

variable "node_group_min_size" {
  description = "Minimum number of nodes in the EKS node group"
  type        = number
  default     = 2
}

variable "node_group_max_size" {
  description = "Maximum number of nodes in the EKS node group"
  type        = number
  default     = 10
}

variable "node_group_desired_size" {
  description = "Desired number of nodes in the EKS node group"
  type        = number
  default     = 3
}

variable "spot_instance_types" {
  description = "EC2 instance types for spot instances"
  type        = list(string)
  default     = ["m5.large", "m5.xlarge", "m4.large", "m4.xlarge"]
}

variable "spot_max_size" {
  description = "Maximum number of spot instances"
  type        = number
  default     = 20
}

variable "spot_desired_size" {
  description = "Desired number of spot instances"
  type        = number
  default     = 0
}

# Database Configuration
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "database_name" {
  description = "Database name"
  type        = string
  default     = "nautilus_trader"
}

variable "database_username" {
  description = "Database username"
  type        = string
  default     = "nautilus"
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
  default     = "securePassword123"
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 1
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the infrastructure"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Feature Flags
variable "enable_monitoring" {
  description = "Enable monitoring stack (Prometheus, Grafana)"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable centralized logging (ELK stack)"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "enable_multi_az" {
  description = "Enable multi-AZ deployment for RDS"
  type        = bool
  default     = true
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling for predictable workloads"
  type        = bool
  default     = false
}

# Environment-specific overrides
variable "environment_config" {
  description = "Environment-specific configuration overrides"
  type = map(object({
    node_group_min_size     = number
    node_group_max_size     = number
    node_group_desired_size = number
    rds_instance_class      = string
    redis_node_type         = string
    enable_multi_az         = bool
    log_retention_days      = number
  }))
  default = {
    dev = {
      node_group_min_size     = 1
      node_group_max_size     = 3
      node_group_desired_size = 1
      rds_instance_class      = "db.t3.micro"
      redis_node_type         = "cache.t3.micro"
      enable_multi_az         = false
      log_retention_days      = 7
    }
    staging = {
      node_group_min_size     = 2
      node_group_max_size     = 5
      node_group_desired_size = 2
      rds_instance_class      = "db.t3.small"
      redis_node_type         = "cache.t3.small"
      enable_multi_az         = false
      log_retention_days      = 14
    }
    prod = {
      node_group_min_size     = 3
      node_group_max_size     = 20
      node_group_desired_size = 5
      rds_instance_class      = "db.r5.large"
      redis_node_type         = "cache.r5.large"
      enable_multi_az         = true
      log_retention_days      = 90
    }
  }
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}