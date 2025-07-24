# Glue Database
resource "aws_glue_catalog_database" "main" {
  name = "${var.project_name}_database"
  
  description = "Database for ${var.project_name} analytics"
}

# Security group for Glue jobs
resource "aws_security_group" "glue_job" {
  name_prefix = "${var.project_name}-glue-job-"
  vpc_id      = var.vpc_id

  # Self-referencing rule for Glue jobs to communicate with each other
  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-glue-job-sg"
  }
}

# Allow Glue jobs to access RDS
resource "aws_security_group_rule" "glue_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.glue_job.id
  security_group_id        = var.rds_security_group_id
}

# Glue connection for RDS
resource "aws_glue_connection" "rds_connection" {
  name = "${var.project_name}-rds-connection"

  connection_properties = {
    JDBC_CONNECTION_URL = "jdbc:postgresql://${var.rds_endpoint}/${var.db_name}"
    USERNAME           = var.db_username
    PASSWORD           = var.db_password
  }

  physical_connection_requirements {
    availability_zone      = data.aws_availability_zones.available.names[0]
    security_group_id_list = [aws_security_group.glue_job.id]
    subnet_id             = var.private_subnet_ids[0]
  }
}

# Create ETL script locally first (using bookmark-based template)
resource "local_file" "etl_script" {
  content = templatefile("${path.module}/etl_job_template_upsert.py", {
    s3_bucket = var.s3_bucket_name
    database_name = aws_glue_catalog_database.main.name
  })
  filename = "${path.module}/../../glue_scripts/etl_job_bookmark.py"
}

# Upload Glue ETL script to S3
resource "aws_s3_object" "etl_script" {
  bucket = var.s3_bucket_name
  key    = "glue-scripts/etl_job_bookmark.py"
  source = local_file.etl_script.filename
  etag   = local_file.etl_script.content_md5

  depends_on = [local_file.etl_script]
}

# Glue ETL Job for customers
resource "aws_glue_job" "customers_etl" {
  name     = "${var.project_name}-customers-etl"
  role_arn = var.glue_role_arn

  command {
    script_location = "s3://${var.s3_bucket_name}/glue-scripts/etl_job_bookmark.py"
    python_version  = "3"
  }

  connections = [aws_glue_connection.rds_connection.name]

  default_arguments = {
    "--job-bookmark-option"     = "job-bookmark-enable"
    "--enable-metrics"          = ""
    "--enable-spark-ui"         = "true"
    "--spark-event-logs-path"   = "s3://${var.s3_bucket_name}/spark-logs/"
    "--TempDir"                 = "s3://${var.s3_bucket_name}/temp/"
    "--source_table"            = "customers"
    "--target_path"             = "s3://${var.s3_bucket_name}/customers/"
    "--database_name"           = aws_glue_catalog_database.main.name
    "--connection_name"         = aws_glue_connection.rds_connection.name
  }

  glue_version = "4.0"
  max_capacity = 2
  timeout      = 60

  tags = {
    Name = "${var.project_name}-customers-etl"
  }
}

# Glue ETL Job for orders
resource "aws_glue_job" "orders_etl" {
  name     = "${var.project_name}-orders-etl"
  role_arn = var.glue_role_arn

  command {
    script_location = "s3://${var.s3_bucket_name}/glue-scripts/etl_job_bookmark.py"
    python_version  = "3"
  }

  connections = [aws_glue_connection.rds_connection.name]

  default_arguments = {
    "--job-bookmark-option"     = "job-bookmark-enable"
    "--enable-metrics"          = ""
    "--enable-spark-ui"         = "true"
    "--spark-event-logs-path"   = "s3://${var.s3_bucket_name}/spark-logs/"
    "--TempDir"                 = "s3://${var.s3_bucket_name}/temp/"
    "--source_table"            = "orders"
    "--target_path"             = "s3://${var.s3_bucket_name}/orders/"
    "--database_name"           = aws_glue_catalog_database.main.name
    "--connection_name"         = aws_glue_connection.rds_connection.name
  }

  glue_version = "4.0"
  max_capacity = 2
  timeout      = 60

  tags = {
    Name = "${var.project_name}-orders-etl"
  }
}

# Glue Crawler for automatic schema discovery and table creation
resource "aws_glue_crawler" "data_lake_crawler" {
  database_name = aws_glue_catalog_database.main.name
  name          = "${var.project_name}-crawler"
  role          = var.glue_role_arn

  # Separate S3 targets for better organization
  s3_target {
    path = "s3://${var.s3_bucket_name}/customers/"
  }
  
  s3_target {
    path = "s3://${var.s3_bucket_name}/orders/"
  }

  # Configuration for better schema detection
  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
      Tables = {
        AddOrUpdateBehavior = "MergeNewColumns"
      }
    }
  })

  # Don't run on a schedule initially - use triggers instead
  tags = {
    Name = "${var.project_name}-crawler"
  }
}

# Glue Trigger to run ETL jobs in sequence (Daily at 1 AM)
resource "aws_glue_trigger" "etl_trigger" {
  name = "${var.project_name}-etl-trigger"
  type = "SCHEDULED"
  
  schedule = "cron(0 1 * * ? *)"  # Run daily at 1 AM
  
  actions {
    job_name = aws_glue_job.customers_etl.name
  }
  
  actions {
    job_name = aws_glue_job.orders_etl.name
  }

  tags = {
    Name = "${var.project_name}-etl-trigger"
  }
}

# Glue Trigger to run crawler after ETL jobs complete
resource "aws_glue_trigger" "crawler_trigger" {
  name = "${var.project_name}-crawler-trigger"
  type = "CONDITIONAL"
  
  actions {
    crawler_name = aws_glue_crawler.data_lake_crawler.name
  }
  
  predicate {
    logical = "AND"
    
    conditions {
      job_name = aws_glue_job.customers_etl.name
      state    = "SUCCEEDED"
    }
    
    conditions {
      job_name = aws_glue_job.orders_etl.name
      state    = "SUCCEEDED"
    }
  }

  tags = {
    Name = "${var.project_name}-crawler-trigger"
  }
}

# Optional: Manual trigger for initial crawler run or troubleshooting
resource "aws_glue_trigger" "crawler_manual_trigger" {
  name = "${var.project_name}-crawler-manual"
  type = "ON_DEMAND"
  
  actions {
    crawler_name = aws_glue_crawler.data_lake_crawler.name
  }

  tags = {
    Name = "${var.project_name}-crawler-manual"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}
