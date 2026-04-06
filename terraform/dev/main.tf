provider "aws" {
  region = "ap -southeast-2"
}

module "dev_infra" {
  source   = "../modules/telemetry_pipe"
  env_name = "dev"
}

terraform {
  backend "local" {} 
}