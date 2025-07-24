terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  profile = "test-prod"
  region  = var.aws_region
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

data "aws_availability_zones" "available" {
  state = "available"
}

# Module calls
module "rds" {
  source = "./modules/rds"
  
  vpc_id               = aws_vpc.main.id
  private_subnet_ids   = aws_subnet.private[*].id
  public_subnet_ids    = aws_subnet.public[*].id  # Added for public access
  project_name         = var.project_name
  db_name              = var.db_name
  db_username          = var.db_username
  db_password          = var.db_password
}

module "s3" {
  source = "./modules/s3"
  
  project_name = var.project_name
}

module "iam" {
  source = "./modules/iam"
  
  project_name = var.project_name
  s3_bucket_arn = module.s3.data_lake_bucket_arn
  rds_endpoint = module.rds.rds_endpoint
  vpc_id = aws_vpc.main.id
  private_subnet_ids = aws_subnet.private[*].id
}

module "glue" {
  source = "./modules/glue"
  
  project_name      = var.project_name
  glue_role_arn     = module.iam.glue_role_arn
  s3_bucket_name    = module.s3.data_lake_bucket_name
  rds_endpoint      = module.rds.rds_endpoint
  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = var.db_password
  vpc_id            = aws_vpc.main.id
  private_subnet_ids = aws_subnet.private[*].id
  rds_security_group_id = module.rds.rds_security_group_id
}

module "athena" {
  source = "./modules/athena"
  
  project_name      = var.project_name
  s3_bucket_name    = module.s3.data_lake_bucket_name
  glue_database_name = module.glue.glue_database_name
}