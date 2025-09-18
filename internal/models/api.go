package models

import "time"

// WorkflowRequest represents a request to run the complete GRC workflow
type WorkflowRequest struct {
	FeedURL string         `json:"feed_url" binding:"required"`
	Config  AnalysisConfig `json:"config" binding:"required"`
}

// WorkflowResponse represents the response from the workflow execution
type WorkflowResponse struct {
	Status    string     `json:"status"`
	ReportID  string     `json:"report_id,omitempty"`
	Report    *Report    `json:"report,omitempty"`
	Error     *APIError  `json:"error,omitempty"`
	Metadata  *Metadata  `json:"metadata,omitempty"`
}

// AnalysisRequest represents a request for GRC analysis
type AnalysisRequest struct {
	Articles []ArticleInput `json:"articles" binding:"required"`
	Config   AnalysisConfig `json:"config" binding:"required"`
}

// AnalysisResponse represents the response from GRC analysis
type AnalysisResponse struct {
	Status   string            `json:"status"`
	Results  []AnalysisResult  `json:"results"`
	Summary  AnalysisSummary   `json:"summary"`
	Error    *APIError         `json:"error,omitempty"`
}

// AnalysisConfig holds configuration for the analysis
type AnalysisConfig struct {
	Model      string   `json:"model"`
	MaxTokens  int      `json:"max_tokens"`
	FocusAreas []string `json:"focus_areas"`
}

// ArticleInput represents an article for analysis
type ArticleInput struct {
	Title     string    `json:"title"`
	URL       string    `json:"url"`
	Content   string    `json:"content"`
	Summary   string    `json:"summary"`
	Source    string    `json:"source"`
	Published time.Time `json:"published"`
}

// AnalysisResult represents the analysis result for a single article
type AnalysisResult struct {
	ArticleURL      string   `json:"article_url"`
	HasGRCContent   bool     `json:"has_grc_content"`
	Regulations     []string `json:"regulations"`
	Frameworks      []string `json:"frameworks"`
	Industries      []string `json:"industries"`
	RegulatoryBodies []string `json:"regulatory_bodies"`
	RiskLevels      []string `json:"risk_levels"`
}

// AnalysisSummary provides an overall summary of the analysis
type AnalysisSummary struct {
	TotalArticles       int      `json:"total_articles"`
	GRCArticles        int      `json:"grc_articles"`
	TopRegulations     []string `json:"top_regulations"`
	TopFrameworks      []string `json:"top_frameworks"`
	AffectedIndustries []string `json:"affected_industries"`
}

// Report represents the generated GRC report
type Report struct {
	Title      string     `json:"title"`
	Content    string     `json:"content"`
	GeneratedAt time.Time `json:"generated_at"`
	Metadata   *Metadata  `json:"metadata,omitempty"`
}

// Metadata holds additional information about the report
type Metadata struct {
	ArticleCount         int      `json:"article_count"`
	GRCArticleCount     int      `json:"grc_article_count"`
	RegulationsMentioned []string `json:"regulations_mentioned"`
	FrameworksReferenced []string `json:"frameworks_referenced"`
	IndustriesAffected   []string `json:"industries_affected"`
	RegulatoryBodies     []string `json:"regulatory_bodies"`
}

// APIError represents an error response
type APIError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Details string `json:"details,omitempty"`
}

// HealthStatus represents the health status of a service
type HealthStatus struct {
	Status    string                    `json:"status"`
	Timestamp time.Time                 `json:"timestamp"`
	Services  map[string]ServiceHealth  `json:"services"`
	Version   string                    `json:"version,omitempty"`
}

// ServiceHealth represents the health of an individual service
type ServiceHealth struct {
	Status string `json:"status"`
	Error  string `json:"error,omitempty"`
}

// GenerateReportRequest represents a request to generate a new report
type GenerateReportRequest struct {
	FeedURL string         `json:"feed_url" binding:"required,url"`
	Config  AnalysisConfig `json:"config" binding:"required"`
}

// GenerateReportResponse represents the response from report generation
type GenerateReportResponse struct {
	ReportID string `json:"report_id"`
	Status   string `json:"status"`
	Message  string `json:"message"`
}

// ListReportsResponse represents the response for listing reports
type ListReportsResponse struct {
	Reports    []ReportSummary `json:"reports"`
	Total      int64           `json:"total"`
	Page       int             `json:"page"`
	PerPage    int             `json:"per_page"`
	TotalPages int             `json:"total_pages"`
}

// ReportSummary represents a summary of a report for listing
type ReportSummary struct {
    ID          string    `json:"id"`
    Title       string    `json:"title"`
    Status      string    `json:"status"`
    GeneratedAt *time.Time `json:"generated_at"`
    CreatedAt   time.Time `json:"created_at"`
    ArticleCount int      `json:"article_count"`
}
