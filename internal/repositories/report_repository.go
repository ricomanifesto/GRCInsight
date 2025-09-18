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

	// Convert models.Report to DynamoDB format
    dynamoReport := &dynamodb.Report{
        Title:     report.Title,
        Content:   report.Content,
        Status:    report.Status,
        SourceURL: report.SourceURL,
        Metadata: dynamodb.ReportMetadata{
            ArticleCount:         report.Metadata.ArticleCount,
            GRCArticleCount:      report.Metadata.GRCArticleCount,
            RegulationsMentioned: report.Metadata.RegulationsMentioned,
            FrameworksReferenced: report.Metadata.FrameworksReferenced,
            IndustriesAffected:   report.Metadata.IndustriesAffected,
            RegulatoryBodies:     report.Metadata.RegulatoryBodies,
        },
    }

	if report.GeneratedAt != nil {
		dynamoReport.GeneratedAt = report.GeneratedAt
	}

    if err := r.repo.CreateReport(ctx, dynamoReport); err != nil {
        return err
    }

    // Update the original report with the generated ID (string)
    report.ID = dynamoReport.ReportID
    report.CreatedAt = r.parseTime(dynamoReport.CreatedAt)
    report.UpdatedAt = r.parseTime(dynamoReport.UpdatedAt)

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

	// Convert DynamoDB result to models.Report
    report := &models.Report{
        ID:        dynamoReport.ReportID,
        Title:     dynamoReport.Title,
        Content:   dynamoReport.Content,
        Status:    dynamoReport.Status,
        SourceURL: dynamoReport.SourceURL,
        CreatedAt: r.parseTime(dynamoReport.CreatedAt),
        UpdatedAt: r.parseTime(dynamoReport.UpdatedAt),
        Metadata: models.ReportMetadata{
            ArticleCount:         dynamoReport.Metadata.ArticleCount,
            GRCArticleCount:      dynamoReport.Metadata.GRCArticleCount,
            RegulationsMentioned: dynamoReport.Metadata.RegulationsMentioned,
            FrameworksReferenced: dynamoReport.Metadata.FrameworksReferenced,
            IndustriesAffected:   dynamoReport.Metadata.IndustriesAffected,
            RegulatoryBodies:     dynamoReport.Metadata.RegulatoryBodies,
        },
    }

	if dynamoReport.GeneratedAt != nil {
		report.GeneratedAt = dynamoReport.GeneratedAt
	}

	return report, nil
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
        report := &models.Report{
            ID:        dynamoReport.ReportID,
            Title:     dynamoReport.Title,
            Content:   dynamoReport.Content,
            Status:    dynamoReport.Status,
            SourceURL: dynamoReport.SourceURL,
            CreatedAt: r.parseTime(dynamoReport.CreatedAt),
            UpdatedAt: r.parseTime(dynamoReport.UpdatedAt),
            Metadata: models.ReportMetadata{
                ArticleCount:         dynamoReport.Metadata.ArticleCount,
                GRCArticleCount:      dynamoReport.Metadata.GRCArticleCount,
                RegulationsMentioned: dynamoReport.Metadata.RegulationsMentioned,
                FrameworksReferenced: dynamoReport.Metadata.FrameworksReferenced,
                IndustriesAffected:   dynamoReport.Metadata.IndustriesAffected,
                RegulatoryBodies:     dynamoReport.Metadata.RegulatoryBodies,
            },
        }

		if dynamoReport.GeneratedAt != nil {
			report.GeneratedAt = dynamoReport.GeneratedAt
		}

		reports = append(reports, report)
	}

	// Return count as length since DynamoDB pagination is different
	total := int64(len(reports))
	return reports, total, nil
}

// Update updates an existing report
func (r *reportRepository) Update(report *models.Report) error {
    ctx := context.Background()

    // Convert models.Report to DynamoDB format
    dynamoReport := &dynamodb.Report{
        ReportID:  report.ID,
        Title:     report.Title,
        Content:   report.Content,
        Status:    report.Status,
        SourceURL: report.SourceURL,
        CreatedAt: dynamodb.ToISO8601(report.CreatedAt), // Preserve original created_at
        Metadata: dynamodb.ReportMetadata{
            ArticleCount:         report.Metadata.ArticleCount,
            GRCArticleCount:      report.Metadata.GRCArticleCount,
            RegulationsMentioned: report.Metadata.RegulationsMentioned,
            FrameworksReferenced: report.Metadata.FrameworksReferenced,
            IndustriesAffected:   report.Metadata.IndustriesAffected,
            RegulatoryBodies:     report.Metadata.RegulatoryBodies,
        },
    }

	if report.GeneratedAt != nil {
		dynamoReport.GeneratedAt = report.GeneratedAt
	}

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

        report := &models.Report{
            ID:        dynamoReport.ReportID,
            Title:     dynamoReport.Title,
            Content:   dynamoReport.Content,
            Status:    dynamoReport.Status,
            SourceURL: dynamoReport.SourceURL,
            CreatedAt: r.parseTime(dynamoReport.CreatedAt),
            UpdatedAt: r.parseTime(dynamoReport.UpdatedAt),
            Metadata: models.ReportMetadata{
                ArticleCount:         dynamoReport.Metadata.ArticleCount,
                GRCArticleCount:      dynamoReport.Metadata.GRCArticleCount,
                RegulationsMentioned: dynamoReport.Metadata.RegulationsMentioned,
                FrameworksReferenced: dynamoReport.Metadata.FrameworksReferenced,
                IndustriesAffected:   dynamoReport.Metadata.IndustriesAffected,
                RegulatoryBodies:     dynamoReport.Metadata.RegulatoryBodies,
            },
        }

		if dynamoReport.GeneratedAt != nil {
			report.GeneratedAt = dynamoReport.GeneratedAt
		}

		reports = append(reports, report)
	}

	return reports, nil
}

// parseTime is a helper function to parse ISO8601 strings back to time.Time
func (r *reportRepository) parseTime(timeStr string) time.Time {
	if t, err := dynamodb.FromISO8601(timeStr); err == nil {
		return t
	}
	return time.Now() // Fallback to current time if parsing fails
}
