package dynamodb

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"
)

// nowFunc is the clock used for stored timestamps.
var nowFunc = time.Now

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

	// JobID is the admitted generation job; the report writer binds completion to it.
	JobID string `dynamodbav:"job_id,omitempty" json:"job_id,omitempty"`
	// Final-outcome fields written once by the report writer.
	TerminalOutcome string `dynamodbav:"terminal_outcome,omitempty" json:"terminal_outcome,omitempty"`
	TerminalReason  string `dynamodbav:"terminal_reason,omitempty" json:"terminal_reason,omitempty"`
	OutcomeSHA256   string `dynamodbav:"outcome_sha256,omitempty" json:"outcome_sha256,omitempty"`
	AppearanceSet   string `dynamodbav:"appearance_set_sha256,omitempty" json:"appearance_set_sha256,omitempty"`
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

	// History fields; empty on legacy rows.
	RecordKind       string `dynamodbav:"record_kind,omitempty" json:"record_kind,omitempty"`
	RevisionID       string `dynamodbav:"revision_id,omitempty" json:"revision_id,omitempty"`
	ContentSHA256    string `dynamodbav:"content_sha256,omitempty" json:"content_sha256,omitempty"`
	AppearanceSet    string `dynamodbav:"appearance_set_sha256,omitempty" json:"appearance_set_sha256,omitempty"`
	Position         int    `dynamodbav:"position,omitempty" json:"position,omitempty"`
	PublishedAt      string `dynamodbav:"published_at,omitempty" json:"published_at,omitempty"`
	PublishedAtKnown *bool  `dynamodbav:"published_at_known,omitempty" json:"published_at_known,omitempty"`
	// Capture provenance of a revision; part of its identity.
	CaptureSHA256         string `dynamodbav:"capture_sha256,omitempty" json:"capture_sha256,omitempty"`
	CapturedContentLength int    `dynamodbav:"captured_content_length,omitempty" json:"captured_content_length,omitempty"`
	CapturedContentSHA256 string `dynamodbav:"captured_content_sha256,omitempty" json:"captured_content_sha256,omitempty"`
	ContentOrigin         string `dynamodbav:"content_origin,omitempty" json:"content_origin,omitempty"`
	ContentTruncated      bool   `dynamodbav:"content_truncated,omitempty" json:"content_truncated,omitempty"`
	// EvidenceStatus is computed when reading; it is never stored.
	EvidenceStatus string `dynamodbav:"-" json:"evidence_status,omitempty"`
}

// NewJobID returns a random identifier for one admitted generation job.
func NewJobID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		panic(fmt.Sprintf("crypto/rand failed: %v", err))
	}
	return "job_" + hex.EncodeToString(b)
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
