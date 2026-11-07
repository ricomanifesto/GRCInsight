package repositories

import (
	"encoding/json"
	"reflect"
	"testing"
	"time"

	"grcinsight/internal/database/dynamodb"
	"grcinsight/internal/database/models"

	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
)

// pythonMetadata is report metadata as the Python Lambda writes it, including
// null values, nested evidence and a stored report plan.
const pythonMetadata = `{
	"article_count": 30,
	"grc_article_count": 12,
	"analysis_mode": "model",
	"fallback_reason": null,
	"source_name": "SentryDigest",
	"source_url": "https://example.com/feed.xml",
	"source_home_url": "https://digest.example/",
	"source_issue_date": "2026-08-13",
	"source_issue_url": "https://digest.example/archive/2026-08-13/",
	"analysis_period": "August 2026",
	"requested_model": "openrouter/example/model",
	"resolved_model": "example/model",
	"source_articles": [{
		"title": "Evidence",
		"url": "https://example.com/evidence",
		"digest_url": "https://digest.example/archive/2026-08-13/#evidence",
		"cves": ["CVE-2026-12345"],
		"snippet": "A retained article passage describes supplier access to customer systems.",
		"article_evidence": [{"origin": "content", "extraction_version": 1, "raw_text": "<p>A retained article passage describes supplier access to customer systems.</p>", "text": "A retained article passage describes supplier access to customer systems."}],
		"effective_date_evidence": null
	}],
	"report_plan": {
		"regulatory_changes": [],
		"control_implications": [{"control_id": "third_party_risk", "priority": "medium", "source_ids": [1], "focus": "supplier access", "evidence_origin": "content", "evidence_excerpt": "A retained article passage describes supplier access to customer systems.", "headline": "Supplier access reaches customer systems", "significance": "Owners should confirm which suppliers hold access."}],
		"industry_impacts": [],
		"executive_brief": {"paragraphs": [{"text": "Supplier access is the period's lead finding.", "source_ids": [1]}]}
	},
	"regulations_mentioned": ["SOX"],
	"frameworks_referenced": [],
	"industries_affected": [],
	"regulatory_bodies": ["SEC"]
}`

func decodeJSON(t *testing.T, text string) map[string]any {
	t.Helper()
	var value map[string]any
	if err := json.Unmarshal([]byte(text), &value); err != nil {
		t.Fatal(err)
	}
	return value
}

func TestPythonWrittenMetadataReadsBackUnchanged(t *testing.T) {
	written := decodeJSON(t, pythonMetadata)
	metadata, err := attributevalue.Marshal(written)
	if err != nil {
		t.Fatal(err)
	}
	item, err := attributevalue.MarshalMap(map[string]any{
		"report_id":    "report-123",
		"title":        "GRC Intelligence Report - 2026-08-13",
		"content":      "## Executive Summary",
		"status":       models.StatusCompleted,
		"generated_at": "2026-08-13T12:00:00Z",
		"created_at":   "2026-08-13T11:00:00Z",
		"updated_at":   "2026-08-13T12:00:00Z",
	})
	if err != nil {
		t.Fatal(err)
	}
	item["metadata"] = metadata

	var stored dynamodb.Report
	if err := attributevalue.UnmarshalMap(item, &stored); err != nil {
		t.Fatal(err)
	}
	report := reportFromDynamo(&stored)
	if report.Metadata.Int("article_count") != 30 {
		t.Fatalf("article count = %d", report.Metadata.Int("article_count"))
	}

	// The HTTP handler encodes the domain report directly.
	encoded, err := json.Marshal(report)
	if err != nil {
		t.Fatal(err)
	}
	var response struct {
		Status   string         `json:"status"`
		Metadata map[string]any `json:"metadata"`
	}
	if err := json.Unmarshal(encoded, &response); err != nil {
		t.Fatal(err)
	}
	if response.Status != models.StatusCompleted {
		t.Fatalf("status = %q", response.Status)
	}
	if !reflect.DeepEqual(response.Metadata, written) {
		t.Fatalf("metadata changed across storage:\n got: %#v\nwant: %#v", response.Metadata, written)
	}
}

func TestReportMetadataRoundTripsThroughDynamoWithoutFieldMapping(t *testing.T) {
	generatedAt := time.Date(2026, time.August, 12, 15, 30, 0, 0, time.UTC)
	domain := &models.Report{
		ID:          "report-123",
		Title:       "GRC Intelligence Report",
		Content:     "Report content",
		Status:      models.StatusCompleted,
		SourceURL:   "https://example.com/feed.xml",
		GeneratedAt: &generatedAt,
		CreatedAt:   generatedAt.Add(-time.Hour),
		UpdatedAt:   generatedAt,
		Metadata:    models.ReportMetadata(decodeJSON(t, pythonMetadata)),
	}

	stored := reportToDynamo(domain)
	if stored.ReportID != "" || stored.CreatedAt != "" || stored.UpdatedAt != "" {
		t.Fatal("create mapping populated persistence-managed fields")
	}
	if stored.GeneratedAt != domain.GeneratedAt {
		t.Fatal("generated-at pointer was not preserved")
	}
	item, err := attributevalue.MarshalMap(stored)
	if err != nil {
		t.Fatal(err)
	}
	var read dynamodb.Report
	if err := attributevalue.UnmarshalMap(item, &read); err != nil {
		t.Fatal(err)
	}
	read.ReportID = domain.ID
	read.CreatedAt = dynamodb.ToISO8601(domain.CreatedAt)
	read.UpdatedAt = dynamodb.ToISO8601(domain.UpdatedAt)
	if got := reportFromDynamo(&read); !reflect.DeepEqual(got, domain) {
		t.Fatalf("round-tripped report mismatch:\n got: %#v\nwant: %#v", got, domain)
	}
}

func TestNewReportStoresEmptyMetadataMap(t *testing.T) {
	stored := reportToDynamo(&models.Report{Status: models.StatusProcessing})
	item, err := attributevalue.MarshalMap(stored)
	if err != nil {
		t.Fatal(err)
	}
	var read dynamodb.Report
	if err := attributevalue.UnmarshalMap(item, &read); err != nil {
		t.Fatal(err)
	}
	if read.Metadata == nil || len(read.Metadata) != 0 {
		t.Fatalf("metadata = %#v, want an empty map", read.Metadata)
	}
}

func TestReportFromDynamoPreservesFallbackReason(t *testing.T) {
	report := reportFromDynamo(&dynamodb.Report{
		ReportID: "report-fallback",
		Metadata: map[string]any{"analysis_mode": "fallback", "fallback_reason": "model unavailable"},
	})
	if report.Metadata["fallback_reason"] != "model unavailable" {
		t.Fatalf("fallback reason = %#v", report.Metadata["fallback_reason"])
	}
}
