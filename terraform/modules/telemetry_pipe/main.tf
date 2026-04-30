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
          "s3:PutObject"
        ]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.data_lake.arn}/*"
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