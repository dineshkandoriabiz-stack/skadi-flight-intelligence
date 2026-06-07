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

# 1. IAM Role: Give Lambda permission to assume a role
resource "aws_iam_role" "lambda_exec" {
  name = "skadi_telemetry_transformer_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# 2. IAM Policy: Give Lambda permission to read/write to your Data Lake and log to CloudWatch
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "skadi_s3_read_write"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "${aws_s3_bucket.data_lake.arn}",
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# 3. Create a ZIP file of your Python code for deployment
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "../../src/processing/lambda_function.py"
  output_path = "lambda_function.zip"
}

# 4. The Lambda Function
resource "aws_lambda_function" "telemetry_transformer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "skadi-bronze-to-silver"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  # Attach the official AWS Data Wrangler (Pandas) Layer so we don't have to bundle the heavy library
  layers = ["arn:aws:lambda:ap-southeast-2:336392948345:layer:AWSSDKPandas-Python311:22"]
}

# 5. S3 Bucket Notification: Tell S3 to trigger the Lambda when a JSON file lands in the bronze folder
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.data_lake.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.telemetry_transformer.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "bronze/telemetry/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# 6. Allow S3 to invoke the Lambda function
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telemetry_transformer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data_lake.arn
}

# ==========================================
# PHASE 5: ATHENA & GLUE ANALYTICS GATEWAY
# ==========================================

# 1. Create a folder in S3 to store Athena query results
resource "aws_s3_object" "athena_results_folder" {
  bucket = aws_s3_bucket.data_lake.id
  key    = "athena-results/"
}

# 2. Create the Glue Data Catalog Database
resource "aws_glue_catalog_database" "skadi_db" {
  name = "skadi_flight_intelligence"
}

# 3. Create the Glue Table (Mapping S3 Parquet to SQL)
resource "aws_glue_catalog_table" "silver_telemetry" {
  name          = "silver_telemetry"
  database_name = aws_glue_catalog_database.skadi_db.name
  table_type    = "EXTERNAL_TABLE"

  # V2 UPGRADE: Physical Partition Keys
  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }

  # V2 UPGRADE: Athena Partition Projection Map
  parameters = {
    "classification"                    = "parquet"
    "projection.enabled"                = "true"
    
    "projection.year.type"              = "integer"
    "projection.year.range"             = "2024,2030"
    
    "projection.month.type"             = "integer"
    "projection.month.range"            = "1,12"
    "projection.month.digits"           = "2"
    
    "projection.day.type"               = "integer"
    "projection.day.range"              = "1,31"
    "projection.day.digits"             = "2"
    
    # Mathematical Map (Note the double $$ to escape Terraform's interpolation)
    "storage.location.template"         = "s3://${aws_s3_bucket.data_lake.id}/silver/telemetry/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    # Point this exactly at your Silver layer
    location      = "s3://${aws_s3_bucket.data_lake.id}/silver/telemetry/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-stream"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = 1
      }
    }

    # Define the schema.
    columns {
      name = "flight_id"
      type = "string"
    }
    columns {
      name = "altitude_ft"
      type = "int"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "timestamp"
      type = "string"
    }
    columns {
      name = "processed_at"
      type = "timestamp"
    }
  }
}