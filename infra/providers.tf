terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local backend by default (state file at infra/terraform.tfstate).
  # If you need remote state later (e.g. another S3 bucket + DynamoDB lock),
  # add it here. For this project, local is enough.
}

provider "aws" {
  region = var.aws_region
}
