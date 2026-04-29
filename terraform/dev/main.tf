terraform {
  backend "s3" {
    # 1. Put the NEW memory bucket name here
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
  # 2. Put your EXISTING Data Lake bucket name here
  bucket_name = "lat-skadi-lake-dev-a00475fc" 
}