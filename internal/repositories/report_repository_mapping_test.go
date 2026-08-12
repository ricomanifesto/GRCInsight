package repositories

import (
	"reflect"
	"testing"
	"time"

	"grcinsight/internal/database/dynamodb"
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
			ArticleCount:         4,
			GRCArticleCount:      3,
			AnalysisMode:         "model",
			RegulationsMentioned: []string{"SOX"},
			FrameworksReferenced: []string{"NIST CSF"},
			IndustriesAffected:   []string{"finance"},
			RegulatoryBodies:     []string{"SEC"},
		},
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

	roundTripped := reportFromDynamo(dynamoReport)
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
