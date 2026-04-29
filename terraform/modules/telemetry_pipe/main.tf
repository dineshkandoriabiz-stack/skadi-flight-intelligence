# 1. The Variable Definition (The "Catcher")
# This tells the module to expect the bucket_name from your dev environment
variable "bucket_name" {
  description = "The unique name for the Data Lake S3 bucket"
  type        = string
}

# 2. The S3 Bucket Resource
# This creates/manages the Data Lake using the name passed to the variable
resource "aws_s3_bucket" "data_lake" {
  bucket = var.bucket_name

  tags = {
    Project     = "Skadi Flight Intelligence"
    Environment = "Dev"
    Layer       = "Data Lake"
  }
}