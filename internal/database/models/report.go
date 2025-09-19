package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"time"
)

// Report represents a GRC intelligence report
type Report struct {
    ID          string         `json:"id"`
	Title       string         `json:"title"`
	Content     string         `json:"content"`
	Status      string         `json:"status"`
	SourceURL   string         `json:"source_url"`
	GeneratedAt *time.Time     `json:"generated_at"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`

	// Metadata stored as JSON
	Metadata ReportMetadata `json:"metadata"`

	// Relationships
	Articles []Article `json:"articles,omitempty"`
}

// ReportMetadata holds additional information about the report
type ReportMetadata struct {
	ArticleCount       int      `json:"article_count"`
	GRCArticleCount    int      `json:"grc_article_count"`
	RegulationsMentioned []string `json:"regulations_mentioned"`
	FrameworksReferenced []string `json:"frameworks_referenced"`
	IndustriesAffected   []string `json:"industries_affected"`
	RegulatoryBodies     []string `json:"regulatory_bodies"`
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
    HasGRCContent bool     `json:"has_grc_content"`
    Regulations   []string `json:"regulations"`
    Frameworks    []string `json:"frameworks"`
    Industries    []string `json:"industries"`
    RegulatoryBodies []string `json:"regulatory_bodies"`
}

// ReportStatus constants
const (
	StatusPending    = "pending"
	StatusProcessing = "processing"
	StatusCompleted  = "completed"
	StatusFailed     = "failed"
)

// BeforeCreate sets default values before creating a report
func (r *Report) BeforeCreate() error {
	if r.Status == "" {
		r.Status = StatusPending
	}
	return nil
}

// Value implements the database/sql/driver.Valuer interface for ReportMetadata
func (m ReportMetadata) Value() (driver.Value, error) {
	return json.Marshal(m)
}

// Scan implements the database/sql.Scanner interface for ReportMetadata
func (m *ReportMetadata) Scan(value interface{}) error {
	if value == nil {
		return nil
	}

	var bytes []byte
	switch v := value.(type) {
	case []byte:
		bytes = v
	case string:
		bytes = []byte(v)
	default:
		return errors.New("type assertion to []byte failed")
	}

	return json.Unmarshal(bytes, &m)
}
