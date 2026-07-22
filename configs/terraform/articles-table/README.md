# Terraform – grcinsight-articles DynamoDB Table

This module creates the DynamoDB table used to persist analyzed articles with the required GSIs:

- Table: `grcinsight-articles`
- PK: `article_id` (S)
- GSIs:
  - `by-report-id` (HASH: `report_id`)
  - `by-url` (HASH: `url`)

## Inputs

- `aws_region` (string, default `us-east-1`)
- `articles_table_name` (string, default `grcinsight-articles`)
- `tags` (map(string), default `{}`)

## Outputs

- `articles_table_name`
- `articles_table_arn`
- `articles_gsi_by_report_id`
- `articles_gsi_by_url`

## Usage

Initialize, review the import plan, and apply:

```sh
cd configs/terraform/articles-table
terraform init
terraform plan \
  -var "aws_region=us-east-1" \
  -var "articles_table_name=grcinsight-articles"
terraform apply \
  -var "aws_region=us-east-1" \
  -var "articles_table_name=grcinsight-articles"
```

The import block adopts the existing table identified by
`articles_table_name` before Terraform plans changes. Keep it for the
default deployment. Remove the import block only when intentionally creating a
new table that does not already exist.

After apply, set the service environment variables:

- `ARTICLES_TABLE_NAME=grcinsight-articles`
- `DDB_TABLE_NAME=grcinsight-reports` (existing reports table)

## Notes

- The Go and Python services already support these names via env vars.
- Queries will prefer GSIs; ensure they are present to avoid fallback scans.
