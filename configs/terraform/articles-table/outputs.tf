output "articles_table_name" {
  description = "Name of the DynamoDB articles table"
  value       = aws_dynamodb_table.articles.name
}

output "articles_table_arn" {
  description = "ARN of the DynamoDB articles table"
  value       = aws_dynamodb_table.articles.arn
}

output "articles_gsi_by_report_id" {
  description = "GSI name for querying by report_id"
  value       = "by-report-id"
}

output "articles_gsi_by_url" {
  description = "GSI name for querying by url"
  value       = "by-url"
}

