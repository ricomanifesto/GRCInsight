package services

import (
	"fmt"
	"time"

	"grcinsight/internal/database/models"
	"grcinsight/internal/repositories"
	apiModels "grcinsight/internal/models"

	"github.com/sirupsen/logrus"
)

// ReportService handles report business logic
type ReportService struct {
    reportRepo    repositories.ReportRepository
    articleRepo   repositories.ArticleRepository
    pythonClient  *PythonServiceClient
    logger        *logrus.Logger
}

// NewReportService creates a new report service
func NewReportService(
	reportRepo repositories.ReportRepository,
	articleRepo repositories.ArticleRepository,
	pythonClient *PythonServiceClient,
	logger *logrus.Logger,
) *ReportService {
	return &ReportService{
		reportRepo:   reportRepo,
		articleRepo:  articleRepo,
		pythonClient: pythonClient,
		logger:       logger,
	}
}

// GenerateReport generates a new GRC report
func (s *ReportService) GenerateReport(req *apiModels.GenerateReportRequest) (*models.Report, error) {
    s.logger.Info("Starting report generation")

    // Create report record
    report := &models.Report{
        Title:     fmt.Sprintf("GRC Intelligence Report - %s", time.Now().Format("2006-01-02")),
        Status:    models.StatusProcessing,
        SourceURL: req.FeedURL,
    }

    if err := s.reportRepo.Create(report); err != nil {
        s.logger.WithError(err).Error("Failed to create report record")
        return nil, fmt.Errorf("failed to create report record: %w", err)
    }

    // Build workflow request
    workflowReq := &apiModels.WorkflowRequest{FeedURL: req.FeedURL, Config: req.Config}

    if s.pythonClient.IsAsync() {
        // Async mode: fire-and-forget, return processing status
        if err := s.pythonClient.RunWorkflowAsync(workflowReq, report.ID); err != nil {
            s.logger.WithError(err).Error("Async Python workflow invocation failed")
            report.Status = models.StatusFailed
            _ = s.reportRepo.Update(report)
            return nil, fmt.Errorf("async workflow invocation failed: %w", err)
        }
        // Do not update content here; Python Lambda will update DynamoDB
        s.logger.WithFields(logrus.Fields{"report_id": report.ID}).Info("Report queued for async processing")
    } else {
        // Sync mode: wait for Python result
        workflowResp, err := s.pythonClient.RunWorkflow(workflowReq)
        if err != nil {
            s.logger.WithError(err).Error("Python workflow failed")
            report.Status = models.StatusFailed
            _ = s.reportRepo.Update(report)
            return nil, fmt.Errorf("workflow execution failed: %w", err)
        }

        // Update report with results
        if workflowResp.Report != nil {
            now := time.Now()
            report.Title = workflowResp.Report.Title
            report.Content = workflowResp.Report.Content
            report.GeneratedAt = &now
            report.Status = models.StatusCompleted

            // Update metadata if available
            if workflowResp.Metadata != nil {
                report.Metadata = models.ReportMetadata{
                    ArticleCount:         workflowResp.Metadata.ArticleCount,
                    GRCArticleCount:      workflowResp.Metadata.GRCArticleCount,
                    RegulationsMentioned: ensureNonNilSlice(workflowResp.Metadata.RegulationsMentioned),
                    FrameworksReferenced: ensureNonNilSlice(workflowResp.Metadata.FrameworksReferenced),
                    IndustriesAffected:   ensureNonNilSlice(workflowResp.Metadata.IndustriesAffected),
                    RegulatoryBodies:     ensureNonNilSlice(workflowResp.Metadata.RegulatoryBodies),
                }
            }
        } else {
            report.Status = models.StatusFailed
            s.logger.Error("No report content received from Python service")
        }

        if err := s.reportRepo.Update(report); err != nil {
            s.logger.WithError(err).Error("Failed to update report")
            return nil, fmt.Errorf("failed to update report: %w", err)
        }
    }

    s.logger.WithFields(logrus.Fields{
        "report_id": report.ID,
        "status":    report.Status,
    }).Info("Report generation completed")

	return report, nil
}

// GetReport retrieves a report by ID
func (s *ReportService) GetReport(id string) (*models.Report, error) {
    report, err := s.reportRepo.GetByID(id)
    if err != nil {
        return nil, fmt.Errorf("failed to get report: %w", err)
    }
    return report, nil
}

// ListReports lists reports with pagination
func (s *ReportService) ListReports(page, perPage int) (*apiModels.ListReportsResponse, error) {
	offset := (page - 1) * perPage
	reports, total, err := s.reportRepo.List(perPage, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list reports: %w", err)
	}

	// Convert to summary format
    summaries := make([]apiModels.ReportSummary, len(reports))
    for i, report := range reports {
        summaries[i] = apiModels.ReportSummary{
            ID:           report.ID,
            Title:        report.Title,
            Status:       report.Status,
            GeneratedAt:  report.GeneratedAt,
            CreatedAt:    report.CreatedAt,
            ArticleCount: report.Metadata.ArticleCount,
        }
    }

	totalPages := int((total + int64(perPage) - 1) / int64(perPage))

	return &apiModels.ListReportsResponse{
		Reports:    summaries,
		Total:      total,
		Page:       page,
		PerPage:    perPage,
		TotalPages: totalPages,
	}, nil
}

// DeleteReport deletes a report by ID
func (s *ReportService) DeleteReport(id string) error {
    if err := s.reportRepo.Delete(id); err != nil {
        return fmt.Errorf("failed to delete report: %w", err)
    }
    return nil
}

// ensureNonNilSlice converts nil slices to empty slices for database storage
func ensureNonNilSlice(slice []string) []string {
	if slice == nil {
		return []string{}
	}
	return slice
}
