package repositories

import (
	"encoding/json"
	"reflect"
	"testing"
	"time"

	"grcinsight/internal/database/dynamodb"

	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"grcinsight/internal/database/models"
)

func TestReportMappingsPreserveFields(t *testing.T) {
	generatedAt := time.Date(2026, time.August, 12, 15, 30, 0, 0, time.UTC)
	domainReport := &models.Report{
		ID:          "report-123",
		Title:       "GRC Intelligence Report",
		Content:     "Report content",
		Status:      models.StatusCompleted,
		SourceURL:   "https://example.com/feed.xml",
		GeneratedAt: &generatedAt,
		CreatedAt:   generatedAt.Add(-time.Hour),
		UpdatedAt:   generatedAt,
		Metadata: models.ReportMetadata{
			ArticleCount:    4,
			GRCArticleCount: 3,
			AnalysisMode:    "model",
			SourceName:      "SentryDigest",
			SourceURL:       "https://example.com/feed.xml",
			SourceHomeURL:   "https://digest.example/",
			SourceIssueDate: "2026-08-13",
			SourceIssueURL:  "https://digest.example/archive/2026-08-13/",
			AnalysisPeriod:  "August 2026",
			RequestedModel:  "openrouter/example/model",
			ResolvedModel:   "google/example-model",
			SourceArticles: []map[string]any{
				{
					"title": "Evidence",
					"url":   "https://example.com/evidence",
					"cves":  []string{"CVE-2026-12345"},
				},
			},
			RegulationsMentioned: []string{"SOX"},
			FrameworksReferenced: []string{"NIST CSF"},
			IndustriesAffected:   []string{"finance"},
			RegulatoryBodies:     []string{"SEC"},
		},
	}

	if err := json.Unmarshal([]byte(`{"report_plan":{"regulatory_changes":[],"control_implications":[{"control_id":"governance","priority":"medium","source_ids":[1]}],"industry_impacts":[]}}`), &domainReport.Metadata); err != nil {
		t.Fatal(err)
	}
	dynamoReport := reportToDynamo(domainReport)
	if dynamoReport.ReportID != "" || dynamoReport.CreatedAt != "" || dynamoReport.UpdatedAt != "" {
		t.Fatal("create mapping populated persistence-managed fields")
	}
	if dynamoReport.GeneratedAt != domainReport.GeneratedAt {
		t.Fatal("generated-at pointer was not preserved")
	}
	dynamoReport.ReportID = domainReport.ID
	dynamoReport.CreatedAt = dynamodb.ToISO8601(domainReport.CreatedAt)
	dynamoReport.UpdatedAt = dynamodb.ToISO8601(domainReport.UpdatedAt)

	attributes, err := attributevalue.MarshalMap(dynamoReport.Metadata.ReportPlan)
	if err != nil {
		t.Fatal(err)
	}
	var storedPlan map[string]any
	if err := attributevalue.UnmarshalMap(attributes, &storedPlan); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(storedPlan, domainReport.Metadata.ReportPlan) {
		t.Fatal("report plan changed during DynamoDB serialization")
	}
	roundTripped := reportFromDynamo(dynamoReport)
	encoded, err := json.Marshal(roundTripped.Metadata)
	if err != nil {
		t.Fatal(err)
	}
	var metadata map[string]any
	if err := json.Unmarshal(encoded, &metadata); err != nil {
		t.Fatal(err)
	}
	if metadata["report_plan"] == nil {
		t.Fatal("report plan lost across storage mappings")
	}
	if !reflect.DeepEqual(roundTripped, domainReport) {
		t.Fatalf("round-tripped report mismatch:\n got: %#v\nwant: %#v", roundTripped, domainReport)
	}
}

func TestReportFromDynamoPreservesFallbackReason(t *testing.T) {
	dynamoReport := &dynamodb.Report{
		ReportID: "report-fallback",
		Metadata: dynamodb.ReportMetadata{
			AnalysisMode:   "fallback",
			FallbackReason: "model unavailable",
		},
	}

	report := reportFromDynamo(dynamoReport)
	if report.Metadata.FallbackReason != "model unavailable" {
		t.Fatalf("fallback reason = %q", report.Metadata.FallbackReason)
	}
}
