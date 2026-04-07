variable "env_name" { type = string }

# 1. Kinesis Stream for real-time telemetry
resource "aws_kinesis_stream" "telemetry" {
  name             = "skadi-telemetry-${var.env_name}"
  shard_count      = 1
  retention_period = 24
}

# 2. S3 Bucket for the Medallion Data Lake
resource "aws_s3_bucket" "datalake" {
  bucket = "lat-skadi-lake-${var.env_name}-${random_id.suffix.hex}"
}

# 3. Create Bronze, Silver, Gold folders
resource "aws_s3_object" "layers" {
  for_each = toset(["bronze/", "silver/", "gold/"])
  bucket   = aws_s3_bucket.datalake.id
  key      = each.value
}

resource "random_id" "suffix" {
  byte_length = 4
}