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

	// JobID identifies the admitted generation job this report belongs to.
	// It authorizes completion, so it is never returned by the API.
	JobID string `json:"-"`
	// TerminalOutcome distinguishes model_completed, refused_fallback and failed
	// while Status keeps its existing completed/failed meaning.
	TerminalOutcome string `json:"terminal_outcome,omitempty"`
	TerminalReason  string `json:"terminal_reason,omitempty"`

	// Relationships
	Articles []Article `json:"articles,omitempty"`
}

// ReportMetadata is report metadata exactly as the report workflow wrote it.
// Go stores and returns it without mapping individual fields.
type ReportMetadata map[string]any

// Int returns a numeric metadata field, or zero when it is absent or not a number.
func (m ReportMetadata) Int(key string) int {
	switch value := m[key].(type) {
	case float64:
		return int(value)
	case int:
		return value
	case int64:
		return int(value)
	}
	return 0
}

// Article represents a source article used in report generation
type Article struct {
	ID        uint      `json:"id"`
	Title     string    `json:"title"`
	URL       string    `json:"url"`
	Content   string    `json:"content"`
	Summary   string    `json:"summary"`
	Source    string    `json:"source"`
	DigestURL string    `json:"digest_url,omitempty"`
	Published time.Time `json:"published"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`

	// GRC Analysis results
	HasGRCContent    bool     `json:"has_grc_content"`
	Regulations      []string `json:"regulations"`
	Frameworks       []string `json:"frameworks"`
	Industries       []string `json:"industries"`
	RegulatoryBodies []string `json:"regulatory_bodies"`

	// History provenance; empty for legacy rows.
	RevisionID     string `json:"revision_id,omitempty"`
	EvidenceStatus string `json:"evidence_status,omitempty"`
	PublishedKnown *bool  `json:"published_known,omitempty"`
}

// ReportStatus constants
const (
	StatusProcessing = "processing"
	StatusCompleted  = "completed"
	StatusFailed     = "failed"
)
