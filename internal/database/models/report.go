package models

import (
	"time"
)

// Report represents a GRC intelligence report
type Report struct {
	ID          string     `json:"id"`
	Title       string     `json:"title"`
	Content     string     `json:"content"`
	Status      string     `json:"status"`
	SourceURL   string     `json:"source_url"`
	GeneratedAt *time.Time `json:"generated_at"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`

	// Metadata stored as JSON
	Metadata ReportMetadata `json:"metadata"`

	// Relationships
	Articles []Article `json:"articles,omitempty"`
}

// ReportMetadata holds additional information about the report
type ReportMetadata struct {
	ArticleCount         int              `json:"article_count"`
	GRCArticleCount      int              `json:"grc_article_count"`
	AnalysisMode         string           `json:"analysis_mode,omitempty"`
	FallbackReason       string           `json:"fallback_reason,omitempty"`
	SourceName           string           `json:"source_name,omitempty"`
	SourceURL            string           `json:"source_url,omitempty"`
	AnalysisPeriod       string           `json:"analysis_period,omitempty"`
	Model                string           `json:"model,omitempty"`
	SourceArticles       []map[string]any `json:"source_articles,omitempty"`
	RegulationsMentioned []string         `json:"regulations_mentioned"`
	FrameworksReferenced []string         `json:"frameworks_referenced"`
	IndustriesAffected   []string         `json:"industries_affected"`
	RegulatoryBodies     []string         `json:"regulatory_bodies"`
}

// Article represents a source article used in report generation
type Article struct {
	ID        uint      `json:"id"`
	Title     string    `json:"title"`
	URL       string    `json:"url"`
	Content   string    `json:"content"`
	Summary   string    `json:"summary"`
	Source    string    `json:"source"`
	Published time.Time `json:"published"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`

	// GRC Analysis results
	HasGRCContent    bool     `json:"has_grc_content"`
	Regulations      []string `json:"regulations"`
	Frameworks       []string `json:"frameworks"`
	Industries       []string `json:"industries"`
	RegulatoryBodies []string `json:"regulatory_bodies"`
}

// ReportStatus constants
const (
	StatusProcessing = "processing"
	StatusCompleted  = "completed"
	StatusFailed     = "failed"
)
