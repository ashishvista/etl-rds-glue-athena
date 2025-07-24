# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  vpc_id      = var.vpc_id

  # Allow VPC internal access
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  # Allow public access (WARNING: This is for development only!)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Allow from anywhere
    description = "Public PostgreSQL access - DEVELOPMENT ONLY"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# DB Subnet Group (using public subnets for true public access)
resource "aws_db_subnet_group" "public" {
  name       = "${var.project_name}-db-subnet-group-public"  # New subnet group
  subnet_ids = var.public_subnet_ids  # Public subnets

  tags = {
    Name = "${var.project_name}-db-subnet-group-public"
  }
}

# Old subnet group - will be removed after migration

# RDS Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-postgres-v2"  # Changed to force recreation
  engine         = "postgres"
  engine_version = "15.8"  # Updated to a more recent stable version
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true
  
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.public.name  # Use the new public subnet group
  
  # Enable public accessibility
  publicly_accessible = true
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  deletion_protection = false
  
  tags = {
    Name = "${var.project_name}-postgres-v2"
  }
}
