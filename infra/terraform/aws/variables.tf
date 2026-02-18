# SentinelForge — AWS Terraform Variables

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "sentinelforge"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ---------- VPC ----------
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "single_nat_gateway" {
  description = "Use single NAT gateway (cost savings)"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ---------- Database ----------
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_storage_gb" {
  description = "Initial storage in GB"
  type        = number
  default     = 20
}

variable "db_max_storage_gb" {
  description = "Max autoscale storage in GB"
  type        = number
  default     = 100
}

variable "db_username" {
  description = "Database admin username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

variable "db_multi_az" {
  description = "Enable multi-AZ for RDS"
  type        = bool
  default     = false
}

# ---------- Redis ----------
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

# ---------- ECS ----------
variable "api_cpu" {
  description = "API task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "API task memory in MB"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Number of API tasks"
  type        = number
  default     = 2
}

# ---------- Auth ----------
variable "jwt_secret_key" {
  description = "JWT secret key (256-bit hex)"
  type        = string
  sensitive   = true
}

variable "admin_username" {
  description = "Default admin username"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "Default admin password (12+ chars, complex)"
  type        = string
  sensitive   = true
}

# ---------- Dashboard ECS ----------
variable "dashboard_cpu" {
  description = "Dashboard task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "dashboard_memory" {
  description = "Dashboard task memory in MB"
  type        = number
  default     = 512
}

variable "dashboard_desired_count" {
  description = "Number of dashboard tasks"
  type        = number
  default     = 1
}
