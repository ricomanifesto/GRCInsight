package services

import (
	"errors"
	"fmt"
	"time"

	"grcinsight/internal/database/dynamodb"
	"grcinsight/internal/database/models"
	apiModels "grcinsight/internal/models"
	"grcinsight/internal/repositories"

	"github.com/sirupsen/logrus"
)

// ReportService handles report business logic
type PythonWorkflowClient interface {
	IsAsync() bool
	RunWorkflowAsync(req *apiModels.WorkflowRequest, job WorkflowJob) error
	RunWorkflowForReport(req *apiModels.WorkflowRequest, job WorkflowJob) error
}

var _ PythonWorkflowClient = (*PythonServiceClient)(nil)

type ReportService struct {
	reportRepo   repositories.ReportRepository
	articleRepo  repositories.ArticleRepository
	pythonClient PythonWorkflowClient
	logger       *logrus.Logger
}

// NewReportService creates a new report service
func NewReportService(
	reportRepo repositories.ReportRepository,
	articleRepo repositories.ArticleRepository,
	pythonClient PythonWorkflowClient,
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
	config, err := req.Config.WithDefaults()
	if err != nil {
		return nil, fmt.Errorf("invalid analysis configuration: %w", err)
	}
	s.logger.Info("Starting report generation")

	// Create report record for one admitted generation job.
	report := &models.Report{
		Title:     fmt.Sprintf("GRC Intelligence Report - %s", time.Now().Format("2006-01-02")),
		Status:    models.StatusProcessing,
		SourceURL: req.FeedURL,
		JobID:     dynamodb.NewJobID(),
	}

	if err := s.reportRepo.Create(report); err != nil {
		s.logger.WithError(err).Error("Failed to create report record")
		return nil, fmt.Errorf("failed to create report record: %w", err)
	}

	workflowReq := &apiModels.WorkflowRequest{FeedURL: req.FeedURL, Config: config}
	job := WorkflowJob{ReportID: report.ID, JobID: report.JobID}

	// The Python report writer is the only component that completes a report, in
	// both modes. Go only records failures it observes, and never over a final outcome.
	if s.pythonClient.IsAsync() {
		if err := s.pythonClient.RunWorkflowAsync(workflowReq, job); err != nil {
			s.logger.WithError(err).Error("Async Python workflow invocation failed")
			s.markFailed(report.ID, "invocation_failed")
			return nil, fmt.Errorf("async workflow invocation failed: %w", err)
		}
		s.logger.WithFields(logrus.Fields{"report_id": report.ID}).Info("Report queued for async processing")
		return report, nil
	}

	if err := s.pythonClient.RunWorkflowForReport(workflowReq, job); err != nil {
		s.logger.WithError(err).Error("Python workflow did not complete the report")
		if !errors.Is(err, ErrCompletionRefused) {
			s.markFailed(report.ID, "workflow_failed")
		}
		return nil, fmt.Errorf("workflow execution failed: %w", err)
	}
	stored, err := s.reportRepo.GetByID(report.ID)
	if err != nil {
		return nil, fmt.Errorf("failed to read completed report: %w", err)
	}
	return stored, nil
}

// markFailed records a Go-observed failure; a final outcome is left untouched.
func (s *ReportService) markFailed(reportID, reason string) {
	err := s.reportRepo.MarkFailedIfOpen(reportID, reason)
	switch {
	case errors.Is(err, dynamodb.ErrReportFinal):
		s.logger.WithField("report_id", reportID).Info("Report already final; failure not recorded")
	case err != nil:
		s.logger.WithError(err).WithField("report_id", reportID).Warn("Failed to record report failure")
	}
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
			ArticleCount: report.Metadata.Int("article_count"),
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

// ListReportArticles lists articles associated with a report
func (s *ReportService) ListReportArticles(reportID string, page, perPage int) (*apiModels.ListArticlesResponse, error) {
	if reportID == "" {
		return nil, fmt.Errorf("reportID is required")
	}

	offset := (page - 1) * perPage
	articles, total, err := s.articleRepo.GetByReportID(reportID, perPage, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to list report articles: %w", err)
	}

	// Map to API model
	apiArticles := make([]apiModels.ArticleRecord, len(articles))
	for i, a := range articles {
		apiArticles[i] = apiModels.ArticleRecord{
			Title:            a.Title,
			URL:              a.URL,
			Content:          a.Content,
			Summary:          a.Summary,
			Source:           a.Source,
			DigestURL:        a.DigestURL,
			Published:        a.Published,
			HasGRCContent:    a.HasGRCContent,
			Regulations:      ensureNonNilSlice(a.Regulations),
			Frameworks:       ensureNonNilSlice(a.Frameworks),
			Industries:       ensureNonNilSlice(a.Industries),
			RegulatoryBodies: ensureNonNilSlice(a.RegulatoryBodies),
			RevisionID:       a.RevisionID,
			EvidenceStatus:   a.EvidenceStatus,
			PublishedKnown:   a.PublishedKnown,
		}
	}

	totalPages := int((total + int64(perPage) - 1) / int64(perPage))
	return &apiModels.ListArticlesResponse{
		Articles:   apiArticles,
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
