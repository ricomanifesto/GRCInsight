terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_dynamodb_table" "articles" {
  name         = var.articles_table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "article_id"

  attribute {
    name = "article_id"
    type = "S"
  }

  # GSIs
  attribute {
    name = "report_id"
    type = "S"
  }

  attribute {
    name = "url"
    type = "S"
  }

  global_secondary_index {
    name            = "by-report-id"
    hash_key        = "report_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "by-url"
    hash_key        = "url"
    projection_type = "ALL"
  }

  tags = var.tags
}

