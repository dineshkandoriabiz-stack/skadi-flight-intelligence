terraform {
  backend "s3" {
    bucket = "skadi-tf-state-a00475fc" 
    key    = "skadi/dev/terraform.tfstate"
    region = "ap-southeast-2"
  }
}

provider "aws" {
  region = "ap-southeast-2"
}

module "dev_infra" {
  source      = "../modules/telemetry_pipe"
  bucket_name = "lat-skadi-lake-dev-a00475fc" 
}

# Adopt the manually created Data Lake
import {
  to = module.dev_infra.aws_s3_bucket.data_lake
  id = "lat-skadi-lake-dev-a00475fc"
}