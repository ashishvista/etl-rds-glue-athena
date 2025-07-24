# Temporary file to check existing RDS instances
data "aws_db_instances" "existing" {}

output "existing_rds_instances" {
  value = data.aws_db_instances.existing.instance_identifiers
}
