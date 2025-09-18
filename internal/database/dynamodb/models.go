package dynamodb

import (
	"fmt"
	"time"
)

// Report represents a GRC intelligence report for DynamoDB
type Report struct {
	ReportID    string          `dynamodbav:"report_id" json:"report_id"`
	Title       string          `dynamodbav:"title" json:"title"`
	Content     string          `dynamodbav:"content" json:"content"`
	Status      string          `dynamodbav:"status" json:"status"`
	SourceURL   string          `dynamodbav:"source_url,omitempty" json:"source_url,omitempty"`
	GeneratedAt *time.Time      `dynamodbav:"generated_at,omitempty" json:"generated_at,omitempty"`
	CreatedAt   string          `dynamodbav:"created_at" json:"created_at"`
	UpdatedAt   string          `dynamodbav:"updated_at" json:"updated_at"`
	Metadata    ReportMetadata  `dynamodbav:"metadata" json:"metadata"`
}

// ReportMetadata holds additional information about the report
type ReportMetadata struct {
	ArticleCount         int      `dynamodbav:"article_count" json:"article_count"`
	GRCArticleCount      int      `dynamodbav:"grc_article_count" json:"grc_article_count"`
	RegulationsMentioned []string `dynamodbav:"regulations_mentioned" json:"regulations_mentioned"`
	FrameworksReferenced []string `dynamodbav:"frameworks_referenced" json:"frameworks_referenced"`
	IndustriesAffected   []string `dynamodbav:"industries_affected" json:"industries_affected"`
	RegulatoryBodies     []string `dynamodbav:"regulatory_bodies" json:"regulatory_bodies"`
}

// ReportStatus constants
const (
	StatusPending    = "pending"
	StatusProcessing = "processing"
	StatusCompleted  = "completed"
	StatusFailed     = "failed"
)

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