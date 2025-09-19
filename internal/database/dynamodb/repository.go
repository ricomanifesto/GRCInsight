package dynamodb

import (
	"context"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/sirupsen/logrus"
)

const (
    TableName        = "grcinsight-reports"
    GSIName          = "by-created-at"
    ArticlesTable    = "grcinsight-articles"
    ArticlesByReport = "by-report-id"
)

// Repository provides DynamoDB operations for reports
type Repository struct {
    client *dynamodb.Client
    logger *logrus.Logger
}

// NewRepository creates a new DynamoDB repository
func NewRepository(client *dynamodb.Client, logger *logrus.Logger) *Repository {
	return &Repository{
		client: client,
		logger: logger,
	}
}

// CreateReport creates a new report in DynamoDB
func (r *Repository) CreateReport(ctx context.Context, report *Report) error {
	now := time.Now()
	report.CreatedAt = ToISO8601(now)
	report.UpdatedAt = ToISO8601(now)

	if report.ReportID == "" {
		report.ReportID = GenerateReportID()
	}

	if report.Status == "" {
		report.Status = StatusPending
	}

	item, err := attributevalue.MarshalMap(report)
	if err != nil {
		return fmt.Errorf("failed to marshal report: %w", err)
	}

	input := &dynamodb.PutItemInput{
		TableName: aws.String(TableName),
		Item:      item,
	}

	_, err = r.client.PutItem(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to create report: %w", err)
	}

	r.logger.WithField("report_id", report.ReportID).Info("Report created successfully")
	return nil
}

// GetReport retrieves a report by ID from DynamoDB
func (r *Repository) GetReport(ctx context.Context, reportID string) (*Report, error) {
	input := &dynamodb.GetItemInput{
		TableName: aws.String(TableName),
		Key: map[string]types.AttributeValue{
			"report_id": &types.AttributeValueMemberS{Value: reportID},
		},
	}

	result, err := r.client.GetItem(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to get report: %w", err)
	}

	if result.Item == nil {
		return nil, fmt.Errorf("report not found: %s", reportID)
	}

	var report Report
	err = attributevalue.UnmarshalMap(result.Item, &report)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal report: %w", err)
	}

	return &report, nil
}

// UpdateReport updates an existing report in DynamoDB
func (r *Repository) UpdateReport(ctx context.Context, report *Report) error {
    if report.ReportID == "" {
        return fmt.Errorf("report_id is required for update")
    }

    // Always update updated_at
    report.UpdatedAt = ToISO8601(time.Now())

    // Prepare values
    metadataAV, err := attributevalue.Marshal(report.Metadata)
    if err != nil {
        return fmt.Errorf("failed to marshal metadata: %w", err)
    }

    exprValues := map[string]types.AttributeValue{
        ":title":      &types.AttributeValueMemberS{Value: report.Title},
        ":content":    &types.AttributeValueMemberS{Value: report.Content},
        ":status":     &types.AttributeValueMemberS{Value: report.Status},
        ":source_url": &types.AttributeValueMemberS{Value: report.SourceURL},
        ":metadata":   metadataAV,
        ":updated_at": &types.AttributeValueMemberS{Value: report.UpdatedAt},
    }

    updateExpr := "SET title = :title, content = :content, #status = :status, source_url = :source_url, metadata = :metadata, updated_at = :updated_at"
    exprNames := map[string]string{"#status": "status"}

    if report.GeneratedAt != nil {
        // Marshal generated_at as ISO8601 string
        exprValues[":generated_at"] = &types.AttributeValueMemberS{Value: report.GeneratedAt.UTC().Format(time.RFC3339)}
        updateExpr += ", generated_at = :generated_at"
    }

    input := &dynamodb.UpdateItemInput{
        TableName:                 aws.String(TableName),
        Key:                       map[string]types.AttributeValue{"report_id": &types.AttributeValueMemberS{Value: report.ReportID}},
        UpdateExpression:          aws.String(updateExpr),
        ExpressionAttributeValues: exprValues,
        ExpressionAttributeNames:  exprNames,
        ConditionExpression:       aws.String("attribute_exists(report_id)"),
        ReturnValues:              types.ReturnValueNone,
    }

    if _, err := r.client.UpdateItem(ctx, input); err != nil {
        return fmt.Errorf("failed to update report: %w", err)
    }

    r.logger.WithField("report_id", report.ReportID).Info("Report updated successfully")
    return nil
}

// ListReports retrieves reports ordered by creation time
func (r *Repository) ListReports(ctx context.Context, limit int32) ([]Report, error) {
	input := &dynamodb.ScanInput{
		TableName: aws.String(TableName),
		Limit:     aws.Int32(limit),
	}

	result, err := r.client.Scan(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to list reports: %w", err)
	}

	var reports []Report
	for _, item := range result.Items {
		var report Report
		err = attributevalue.UnmarshalMap(item, &report)
		if err != nil {
			r.logger.WithError(err).Error("Failed to unmarshal report item")
			continue
		}
		reports = append(reports, report)
	}

	return reports, nil
}

// DeleteReport removes a report from DynamoDB
func (r *Repository) DeleteReport(ctx context.Context, reportID string) error {
	input := &dynamodb.DeleteItemInput{
		TableName: aws.String(TableName),
		Key: map[string]types.AttributeValue{
			"report_id": &types.AttributeValueMemberS{Value: reportID},
		},
		ConditionExpression: aws.String("attribute_exists(report_id)"),
	}

	_, err := r.client.DeleteItem(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to delete report: %w", err)
	}

	r.logger.WithField("report_id", reportID).Info("Report deleted successfully")
	return nil
}

// UpdateReportStatus updates only the status field of a report
func (r *Repository) UpdateReportStatus(ctx context.Context, reportID, status string) error {
	input := &dynamodb.UpdateItemInput{
		TableName: aws.String(TableName),
		Key: map[string]types.AttributeValue{
			"report_id": &types.AttributeValueMemberS{Value: reportID},
		},
		UpdateExpression: aws.String("SET #status = :status, updated_at = :updated_at"),
		ExpressionAttributeNames: map[string]string{
			"#status": "status",
		},
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":status":     &types.AttributeValueMemberS{Value: status},
			":updated_at": &types.AttributeValueMemberS{Value: ToISO8601(time.Now())},
		},
		ConditionExpression: aws.String("attribute_exists(report_id)"),
	}

	_, err := r.client.UpdateItem(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to update report status: %w", err)
	}

	r.logger.WithFields(logrus.Fields{
		"report_id": reportID,
		"status":    status,
	}).Info("Report status updated")
	return nil
}

// HealthCheck verifies the DynamoDB connection and table access
func (r *Repository) HealthCheck(ctx context.Context) error {
	input := &dynamodb.DescribeTableInput{
		TableName: aws.String(TableName),
	}

	_, err := r.client.DescribeTable(ctx, input)
	if err != nil {
		return fmt.Errorf("dynamodb health check failed: %w", err)
	}

	return nil
}

// ===== Article operations =====

// CreateArticle stores a new article
func (r *Repository) CreateArticle(ctx context.Context, art *Article) error {
    now := time.Now()
    if art.CreatedAt == "" {
        art.CreatedAt = ToISO8601(now)
    }
    art.UpdatedAt = ToISO8601(now)

    item, err := attributevalue.MarshalMap(art)
    if err != nil {
        return fmt.Errorf("failed to marshal article: %w", err)
    }
    input := &dynamodb.PutItemInput{
        TableName: aws.String(ArticlesTable),
        Item:      item,
        // No condition; overwrite allowed for idempotency
    }
    if _, err := r.client.PutItem(ctx, input); err != nil {
        return fmt.Errorf("failed to create article: %w", err)
    }
    r.logger.WithField("article_id", art.ArticleID).Info("Article created")
    return nil
}

// GetArticleByID fetches an article by its ArticleID
func (r *Repository) GetArticleByID(ctx context.Context, articleID string) (*Article, error) {
    input := &dynamodb.GetItemInput{
        TableName: aws.String(ArticlesTable),
        Key: map[string]types.AttributeValue{
            "article_id": &types.AttributeValueMemberS{Value: articleID},
        },
    }
    result, err := r.client.GetItem(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("failed to get article: %w", err)
    }
    if result.Item == nil {
        return nil, fmt.Errorf("article not found: %s", articleID)
    }
    var art Article
    if err := attributevalue.UnmarshalMap(result.Item, &art); err != nil {
        return nil, fmt.Errorf("failed to unmarshal article: %w", err)
    }
    return &art, nil
}

// GetArticleByNumericID finds article by numeric_id (uint32 hash)
func (r *Repository) GetArticleByNumericID(ctx context.Context, numericID uint32) (*Article, error) {
    // Scan with filter on numeric_id (simple implementation; consider GSI if needed)
    input := &dynamodb.ScanInput{
        TableName:        aws.String(ArticlesTable),
        FilterExpression: aws.String("numeric_id = :nid"),
        ExpressionAttributeValues: map[string]types.AttributeValue{
            ":nid": &types.AttributeValueMemberN{Value: fmt.Sprintf("%d", numericID)},
        },
        Limit: aws.Int32(1),
    }
    out, err := r.client.Scan(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("failed to scan articles: %w", err)
    }
    if len(out.Items) == 0 {
        return nil, fmt.Errorf("article not found")
    }
    var art Article
    if err := attributevalue.UnmarshalMap(out.Items[0], &art); err != nil {
        return nil, fmt.Errorf("failed to unmarshal article: %w", err)
    }
    return &art, nil
}

// GetArticleByURL finds article by URL
func (r *Repository) GetArticleByURL(ctx context.Context, url string) (*Article, error) {
    // Scan with filter on url (consider adding a GSI on url for production)
    input := &dynamodb.ScanInput{
        TableName:        aws.String(ArticlesTable),
        FilterExpression: aws.String("url = :u"),
        ExpressionAttributeValues: map[string]types.AttributeValue{
            ":u": &types.AttributeValueMemberS{Value: url},
        },
        Limit: aws.Int32(1),
    }
    out, err := r.client.Scan(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("failed to scan articles: %w", err)
    }
    if len(out.Items) == 0 {
        return nil, fmt.Errorf("article not found")
    }
    var art Article
    if err := attributevalue.UnmarshalMap(out.Items[0], &art); err != nil {
        return nil, fmt.Errorf("failed to unmarshal article: %w", err)
    }
    return &art, nil
}

// GetArticlesByReportID queries articles by report_id, using GSI if available, else scans
func (r *Repository) GetArticlesByReportID(ctx context.Context, reportID string, limit, offset int32) ([]Article, error) {
    // Try query on GSI first
    input := &dynamodb.QueryInput{
        TableName:              aws.String(ArticlesTable),
        IndexName:              aws.String(ArticlesByReport),
        KeyConditionExpression: aws.String("report_id = :rid"),
        ExpressionAttributeValues: map[string]types.AttributeValue{
            ":rid": &types.AttributeValueMemberS{Value: reportID},
        },
        Limit: aws.Int32(limit + offset),
    }
    var items []map[string]types.AttributeValue
    if out, err := r.client.Query(ctx, input); err == nil {
        items = out.Items
    } else {
        // Fallback to scan
        scanIn := &dynamodb.ScanInput{
            TableName:        aws.String(ArticlesTable),
            FilterExpression: aws.String("report_id = :rid"),
            ExpressionAttributeValues: map[string]types.AttributeValue{
                ":rid": &types.AttributeValueMemberS{Value: reportID},
            },
            Limit: aws.Int32(limit + offset),
        }
        out2, err2 := r.client.Scan(ctx, scanIn)
        if err2 != nil {
            return nil, fmt.Errorf("failed to get articles by report id: %w", err2)
        }
        items = out2.Items
    }

    if int32(len(items)) > offset {
        items = items[offset:]
    } else {
        items = []map[string]types.AttributeValue{}
    }
    if int32(len(items)) > limit {
        items = items[:limit]
    }

    var arts []Article
    for _, it := range items {
        var a Article
        if err := attributevalue.UnmarshalMap(it, &a); err == nil {
            arts = append(arts, a)
        }
    }
    return arts, nil
}

// ListArticles returns up to limit articles; ignores offset (naive skip)
func (r *Repository) ListArticles(ctx context.Context, limit, offset int32) ([]Article, error) {
    input := &dynamodb.ScanInput{
        TableName: aws.String(ArticlesTable),
        Limit:     aws.Int32(limit + offset),
    }
    out, err := r.client.Scan(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("failed to list articles: %w", err)
    }
    items := out.Items
    if int32(len(items)) > offset {
        items = items[offset:]
    } else {
        items = []map[string]types.AttributeValue{}
    }
    if int32(len(items)) > limit {
        items = items[:limit]
    }
    var arts []Article
    for _, it := range items {
        var a Article
        if err := attributevalue.UnmarshalMap(it, &a); err == nil {
            arts = append(arts, a)
        }
    }
    return arts, nil
}

// UpdateArticle updates fields of an article
func (r *Repository) UpdateArticle(ctx context.Context, art *Article) error {
    if art.ArticleID == "" {
        return fmt.Errorf("article_id is required")
    }
    art.UpdatedAt = ToISO8601(time.Now())

    avMeta, err := attributevalue.MarshalMap(map[string]interface{}{})
    if err != nil {
        _ = avMeta // not used; placeholder keep to avoid unused var in case of future meta
    }

    exprValues := map[string]types.AttributeValue{
        ":title":     &types.AttributeValueMemberS{Value: art.Title},
        ":content":   &types.AttributeValueMemberS{Value: art.Content},
        ":summary":   &types.AttributeValueMemberS{Value: art.Summary},
        ":source":    &types.AttributeValueMemberS{Value: art.Source},
        ":url":       &types.AttributeValueMemberS{Value: art.URL},
        ":published": &types.AttributeValueMemberS{Value: art.Published},
        ":updated_at": &types.AttributeValueMemberS{Value: art.UpdatedAt},
        ":has_grc":   &types.AttributeValueMemberBOOL{Value: art.HasGRCContent},
    }
    regsAV, _ := attributevalue.Marshal(art.Regulations)
    fwAV, _ := attributevalue.Marshal(art.Frameworks)
    indAV, _ := attributevalue.Marshal(art.Industries)
    bodiesAV, _ := attributevalue.Marshal(art.RegulatoryBodies)
    exprValues[":regs"] = regsAV
    exprValues[":fw"] = fwAV
    exprValues[":inds"] = indAV
    exprValues[":bodies"] = bodiesAV

    updateExpr := "SET title = :title, content = :content, summary = :summary, source = :source, url = :url, published = :published, has_grc_content = :has_grc, regulations = :regs, frameworks = :fw, industries = :inds, regulatory_bodies = :bodies, updated_at = :updated_at"

    input := &dynamodb.UpdateItemInput{
        TableName:                 aws.String(ArticlesTable),
        Key:                       map[string]types.AttributeValue{"article_id": &types.AttributeValueMemberS{Value: art.ArticleID}},
        UpdateExpression:          aws.String(updateExpr),
        ExpressionAttributeValues: exprValues,
        ReturnValues:              types.ReturnValueNone,
        ConditionExpression:       aws.String("attribute_exists(article_id)"),
    }
    if _, err := r.client.UpdateItem(ctx, input); err != nil {
        return fmt.Errorf("failed to update article: %w", err)
    }
    return nil
}

// DeleteArticle deletes an article by ID
func (r *Repository) DeleteArticle(ctx context.Context, articleID string) error {
    input := &dynamodb.DeleteItemInput{
        TableName: aws.String(ArticlesTable),
        Key: map[string]types.AttributeValue{
            "article_id": &types.AttributeValueMemberS{Value: articleID},
        },
        ConditionExpression: aws.String("attribute_exists(article_id)"),
    }
    if _, err := r.client.DeleteItem(ctx, input); err != nil {
        return fmt.Errorf("failed to delete article: %w", err)
    }
    return nil
}

// GetGRCArticles returns articles flagged as GRC content
func (r *Repository) GetGRCArticles(ctx context.Context, limit, offset int32) ([]Article, error) {
    input := &dynamodb.ScanInput{
        TableName:        aws.String(ArticlesTable),
        FilterExpression: aws.String("has_grc_content = :t"),
        ExpressionAttributeValues: map[string]types.AttributeValue{
            ":t": &types.AttributeValueMemberBOOL{Value: true},
        },
        Limit: aws.Int32(limit + offset),
    }
    out, err := r.client.Scan(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("failed to scan GRC articles: %w", err)
    }
    items := out.Items
    if int32(len(items)) > offset {
        items = items[offset:]
    } else {
        items = []map[string]types.AttributeValue{}
    }
    if int32(len(items)) > limit {
        items = items[:limit]
    }
    var arts []Article
    for _, it := range items {
        var a Article
        if err := attributevalue.UnmarshalMap(it, &a); err == nil {
            arts = append(arts, a)
        }
    }
    return arts, nil
}
