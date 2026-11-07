package models

import (
	"bytes"
	"encoding/json"
	"errors"
	"time"
)

// WorkflowRequest represents a request to run the complete GRC workflow
type WorkflowRequest struct {
	FeedURL string            `json:"feed_url" binding:"required"`
	Config  GRCAnalysisConfig `json:"config" binding:"required"`
}

// WorkflowResponse represents the response from the workflow execution
type WorkflowResponse struct {
	Status   string          `json:"status"`
	ReportID string          `json:"report_id,omitempty"`
	Report   *Report         `json:"report,omitempty"`
	Error    *APIError       `json:"error,omitempty"`
	Metadata map[string]any  `json:"metadata,omitempty"`
	Articles []ArticleRecord `json:"articles,omitempty"`
}

// GRCAnalysisConfig holds configuration for the analysis
type GRCAnalysisConfig struct {
	Model      string   `json:"model"`
	MaxTokens  int      `json:"max_tokens"`
	FocusAreas []string `json:"focus_areas"`
}

// MaxOutputTokens is the omitted-request default and the server output ceiling.
const MaxOutputTokens = 16000

// WithDefaults preserves the zero-value Go construction contract. Explicit JSON
// zero is rejected by UnmarshalJSON, while omitted/programmatic zero means unset.
func (c GRCAnalysisConfig) WithDefaults() (GRCAnalysisConfig, error) {
	if c.MaxTokens == 0 {
		c.MaxTokens = MaxOutputTokens
	}
	if c.MaxTokens < 1 || c.MaxTokens > MaxOutputTokens {
		return c, errors.New("max_tokens must be an integer between 1 and 16000")
	}
	return c, nil
}

func (c *GRCAnalysisConfig) UnmarshalJSON(data []byte) error {
	if bytes.Equal(bytes.TrimSpace(data), []byte("null")) {
		return errors.New("analysis config must be an object")
	}
	var wire struct {
		Model      string          `json:"model"`
		MaxTokens  json.RawMessage `json:"max_tokens"`
		FocusAreas []string        `json:"focus_areas"`
	}
	if err := json.Unmarshal(data, &wire); err != nil {
		return err
	}
	value := GRCAnalysisConfig{Model: wire.Model, MaxTokens: MaxOutputTokens, FocusAreas: wire.FocusAreas}
	if wire.MaxTokens != nil {
		if bytes.Equal(bytes.TrimSpace(wire.MaxTokens), []byte("null")) ||
			json.Unmarshal(wire.MaxTokens, &value.MaxTokens) != nil || value.MaxTokens == 0 {
			return errors.New("max_tokens must be an integer between 1 and 16000")
		}
	}
	normalized, err := value.WithDefaults()
	if err != nil {
		return err
	}
	*c = normalized
	return nil
}

func (c GRCAnalysisConfig) MarshalJSON() ([]byte, error) {
	normalized, err := c.WithDefaults()
	if err != nil {
		return nil, err
	}
	type wireConfig GRCAnalysisConfig
	return json.Marshal(wireConfig(normalized))
}

// ArticleRecord represents an article with GRC analysis fields
type ArticleRecord struct {
	Title            string    `json:"title"`
	URL              string    `json:"url"`
	Content          string    `json:"content"`
	Summary          string    `json:"summary"`
	Source           string    `json:"source"`
	DigestURL        string    `json:"digest_url,omitempty"`
	Published        time.Time `json:"published"`
	HasGRCContent    bool      `json:"has_grc_content"`
	Regulations      []string  `json:"regulations"`
	Frameworks       []string  `json:"frameworks"`
	Industries       []string  `json:"industries"`
	RegulatoryBodies []string  `json:"regulatory_bodies"`
}

// ListArticlesResponse represents a paginated list of articles
type ListArticlesResponse struct {
	Articles   []ArticleRecord `json:"articles"`
	Total      int64           `json:"total"`
	Page       int             `json:"page"`
	PerPage    int             `json:"per_page"`
	TotalPages int             `json:"total_pages"`
}

// Report represents the generated GRC report
type Report struct {
	Title       string         `json:"title"`
	Content     string         `json:"content"`
	GeneratedAt time.Time      `json:"generated_at"`
	Metadata    map[string]any `json:"metadata,omitempty"`
}

// APIError represents an error response
type APIError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Details string `json:"details,omitempty"`
}

// HealthStatus represents the health status of a service
type HealthStatus struct {
	Status    string                   `json:"status"`
	Timestamp time.Time                `json:"timestamp"`
	Services  map[string]ServiceHealth `json:"services"`
	Version   string                   `json:"version,omitempty"`
}

// ServiceHealth represents the health of an individual service
type ServiceHealth struct {
	Status string `json:"status"`
	Error  string `json:"error,omitempty"`
}

// GenerateReportRequest represents a request to generate a new report
type GenerateReportRequest struct {
	FeedURL string            `json:"feed_url" binding:"required,url"`
	Config  GRCAnalysisConfig `json:"config" binding:"required"`
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
	ID           string     `json:"id"`
	Title        string     `json:"title"`
	Status       string     `json:"status"`
	GeneratedAt  *time.Time `json:"generated_at"`
	CreatedAt    time.Time  `json:"created_at"`
	ArticleCount int        `json:"article_count"`
}
