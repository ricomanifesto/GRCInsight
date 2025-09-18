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
	TableName = "grcinsight-reports"
	GSIName   = "by-created-at"
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
