# GRCInsight Articles Table

This Terraform module manages the DynamoDB table that stores analyzed source articles.

The table uses on-demand billing and has three keys:

- `article_id`: primary key.
- `report_id`: `by-report-id` index for the articles in one report.
- `url`: `by-url` index for finding an article by source URL.

## Inputs

| Variable | Default | Purpose |
|---|---|---|
| `aws_region` | `us-east-1` | AWS region |
| `articles_table_name` | `grcinsight-articles` | Table name |
| `tags` | `{}` | Resource tags |

## Apply to the Existing Table

The checked-in `imports.tf` tells Terraform to adopt an existing table named by `articles_table_name`.

```bash
cd configs/terraform/articles-table
terraform init
terraform fmt -check
terraform validate
terraform plan \
  -var 'aws_region=us-east-1' \
  -var 'articles_table_name=grcinsight-articles'
terraform apply \
  -var 'aws_region=us-east-1' \
  -var 'articles_table_name=grcinsight-articles'
```

Review the plan before applying it. If the named table does not already exist, remove the import block only when you intend Terraform to create a new table.

## Service Configuration

After applying, set:

```bash
ARTICLES_TABLE_NAME=grcinsight-articles
DDB_TABLE_NAME=grcinsight-reports
```

`ARTICLES_TABLE_NAME` selects this article table. `DDB_TABLE_NAME` selects the separate reports table.

## Outputs

- `articles_table_name`
- `articles_table_arn`
- `articles_gsi_by_report_id`
- `articles_gsi_by_url`
