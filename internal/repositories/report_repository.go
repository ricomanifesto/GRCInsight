package repositories

import (
	"context"
	"time"

	"grcinsight/internal/database/dynamodb"
	"grcinsight/internal/database/models"
)

// reportRepository implements ReportRepository interface using DynamoDB
type reportRepository struct {
	repo *dynamodb.Repository
}

// NewReportRepository creates a new DynamoDB-based report repository
func NewReportRepository(repo *dynamodb.Repository) ReportRepository {
	return &reportRepository{repo: repo}
}

// Create creates a new report
func (r *reportRepository) Create(report *models.Report) error {
	ctx := context.Background()
	dynamoReport := reportToDynamo(report)

	if err := r.repo.CreateReport(ctx, dynamoReport); err != nil {
		return err
	}

	// Update the original report with the generated ID (string)
	report.ID = dynamoReport.ReportID
	report.CreatedAt = parseDynamoTime(dynamoReport.CreatedAt)
	report.UpdatedAt = parseDynamoTime(dynamoReport.UpdatedAt)

	return nil
}

// GetByID retrieves a report by ID
func (r *reportRepository) GetByID(id string) (*models.Report, error) {
	ctx := context.Background()
	reportID := id

	dynamoReport, err := r.repo.GetReport(ctx, reportID)
	if err != nil {
		return nil, err
	}

	return reportFromDynamo(dynamoReport), nil
}

// List retrieves reports with pagination
func (r *reportRepository) List(limit, offset int) ([]*models.Report, int64, error) {
	ctx := context.Background()

	// DynamoDB doesn't support traditional offset-based pagination
	// For simplicity, we'll use limit and return available reports
	dynamoReports, err := r.repo.ListReports(ctx, int32(limit))
	if err != nil {
		return nil, 0, err
	}

	var reports []*models.Report
	for _, dynamoReport := range dynamoReports {
		reports = append(reports, reportFromDynamo(&dynamoReport))
	}

	// Return count as length since DynamoDB pagination is different
	total := int64(len(reports))
	return reports, total, nil
}

// Update updates an existing report
func (r *reportRepository) Update(report *models.Report) error {
	ctx := context.Background()
	dynamoReport := reportToDynamo(report)
	dynamoReport.ReportID = report.ID
	dynamoReport.CreatedAt = dynamodb.ToISO8601(report.CreatedAt)
	return r.repo.UpdateReport(ctx, dynamoReport)
}

// Delete deletes a report (DynamoDB doesn't have soft delete, so this is hard delete)
func (r *reportRepository) Delete(id string) error {
	ctx := context.Background()
	return r.repo.DeleteReport(ctx, id)
}

// GetByStatus retrieves reports by status
func (r *reportRepository) GetByStatus(status string) ([]*models.Report, error) {
	ctx := context.Background()

	// For simplicity, list all reports and filter by status
	// In production, you might want to create a GSI for status queries
	dynamoReports, err := r.repo.ListReports(ctx, 100) // Get up to 100 reports
	if err != nil {
		return nil, err
	}

	var reports []*models.Report
	for _, dynamoReport := range dynamoReports {
		if dynamoReport.Status != status {
			continue
		}
		reports = append(reports, reportFromDynamo(&dynamoReport))
	}

	return reports, nil
}

func reportToDynamo(report *models.Report) *dynamodb.Report {
	return &dynamodb.Report{
		Title:       report.Title,
		Content:     report.Content,
		Status:      report.Status,
		SourceURL:   report.SourceURL,
		GeneratedAt: report.GeneratedAt,
		Metadata: dynamodb.ReportMetadata{
			ArticleCount:         report.Metadata.ArticleCount,
			GRCArticleCount:      report.Metadata.GRCArticleCount,
			AnalysisMode:         report.Metadata.AnalysisMode,
			FallbackReason:       report.Metadata.FallbackReason,
			RegulationsMentioned: report.Metadata.RegulationsMentioned,
			FrameworksReferenced: report.Metadata.FrameworksReferenced,
			IndustriesAffected:   report.Metadata.IndustriesAffected,
			RegulatoryBodies:     report.Metadata.RegulatoryBodies,
		},
	}
}

func reportFromDynamo(report *dynamodb.Report) *models.Report {
	return &models.Report{
		ID:          report.ReportID,
		Title:       report.Title,
		Content:     report.Content,
		Status:      report.Status,
		SourceURL:   report.SourceURL,
		GeneratedAt: report.GeneratedAt,
		CreatedAt:   parseDynamoTime(report.CreatedAt),
		UpdatedAt:   parseDynamoTime(report.UpdatedAt),
		Metadata: models.ReportMetadata{
			ArticleCount:         report.Metadata.ArticleCount,
			GRCArticleCount:      report.Metadata.GRCArticleCount,
			AnalysisMode:         report.Metadata.AnalysisMode,
			FallbackReason:       report.Metadata.FallbackReason,
			RegulationsMentioned: report.Metadata.RegulationsMentioned,
			FrameworksReferenced: report.Metadata.FrameworksReferenced,
			IndustriesAffected:   report.Metadata.IndustriesAffected,
			RegulatoryBodies:     report.Metadata.RegulatoryBodies,
		},
	}
}

func parseDynamoTime(timeStr string) time.Time {
	if t, err := dynamodb.FromISO8601(timeStr); err == nil {
		return t
	}
	return time.Now()
}
