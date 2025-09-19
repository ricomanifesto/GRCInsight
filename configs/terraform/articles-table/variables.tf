variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "us-east-1"
}

variable "articles_table_name" {
  description = "DynamoDB table name for analyzed articles"
  type        = string
  default     = "grcinsight-articles"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

