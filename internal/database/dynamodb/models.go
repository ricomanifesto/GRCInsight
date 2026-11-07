package dynamodb

import (
	"fmt"
	"time"
)

// Report represents a GRC intelligence report for DynamoDB
type Report struct {
	ReportID    string         `dynamodbav:"report_id" json:"report_id"`
	Title       string         `dynamodbav:"title" json:"title"`
	Content     string         `dynamodbav:"content" json:"content"`
	Status      string         `dynamodbav:"status" json:"status"`
	SourceURL   string         `dynamodbav:"source_url,omitempty" json:"source_url,omitempty"`
	GeneratedAt *time.Time     `dynamodbav:"generated_at,omitempty" json:"generated_at,omitempty"`
	CreatedAt   string         `dynamodbav:"created_at" json:"created_at"`
	UpdatedAt   string         `dynamodbav:"updated_at" json:"updated_at"`
	Metadata    map[string]any `dynamodbav:"metadata" json:"metadata"`
}

// ReportStatus constants
const (
	StatusPending    = "pending"
	StatusProcessing = "processing"
	StatusCompleted  = "completed"
	StatusFailed     = "failed"
)

// Article represents an article stored in DynamoDB
type Article struct {
	ArticleID string `dynamodbav:"article_id" json:"article_id"`
	NumericID uint32 `dynamodbav:"numeric_id" json:"numeric_id"`
	ReportID  string `dynamodbav:"report_id" json:"report_id"`
	Title     string `dynamodbav:"title" json:"title"`
	URL       string `dynamodbav:"url" json:"url"`
	Content   string `dynamodbav:"content" json:"content"`
	Summary   string `dynamodbav:"summary" json:"summary"`
	Source    string `dynamodbav:"source" json:"source"`
	DigestURL string `dynamodbav:"digest_url,omitempty" json:"digest_url,omitempty"`
	Published string `dynamodbav:"published" json:"published"`
	CreatedAt string `dynamodbav:"created_at" json:"created_at"`
	UpdatedAt string `dynamodbav:"updated_at" json:"updated_at"`

	// GRC Analysis results
	HasGRCContent    bool     `dynamodbav:"has_grc_content" json:"has_grc_content"`
	Regulations      []string `dynamodbav:"regulations" json:"regulations"`
	Frameworks       []string `dynamodbav:"frameworks" json:"frameworks"`
	Industries       []string `dynamodbav:"industries" json:"industries"`
	RegulatoryBodies []string `dynamodbav:"regulatory_bodies" json:"regulatory_bodies"`
}

// GenerateReportID creates a unique ID for a new report
func GenerateReportID() string {
	return "report_" + time.Now().Format("20060102_150405") + "_" + generateRandomSuffix()
}

// generateRandomSuffix creates a short random suffix for report IDs
func generateRandomSuffix() string {
	// Use nanosecond timestamp for better uniqueness
	return fmt.Sprintf("%03d", time.Now().Nanosecond()%1000)
}

// ToISO8601 converts a time.Time to ISO8601 string format for DynamoDB
func ToISO8601(t time.Time) string {
	return t.UTC().Format(time.RFC3339)
}

// FromISO8601 converts an ISO8601 string back to time.Time
func FromISO8601(s string) (time.Time, error) {
	return time.Parse(time.RFC3339, s)
}
