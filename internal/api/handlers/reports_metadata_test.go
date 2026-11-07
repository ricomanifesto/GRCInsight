package handlers

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
	"time"

	dbmodels "grcinsight/internal/database/models"
	"grcinsight/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

type storedReportRepo struct{ report *dbmodels.Report }

func (r *storedReportRepo) Create(*dbmodels.Report) error { return nil }
func (r *storedReportRepo) GetByID(string) (*dbmodels.Report, error) {
	return r.report, nil
}
func (r *storedReportRepo) List(int, int) ([]*dbmodels.Report, int64, error) {
	return []*dbmodels.Report{r.report}, 1, nil
}
func (r *storedReportRepo) Update(*dbmodels.Report) error { return nil }
func (r *storedReportRepo) Delete(string) error           { return nil }
func (r *storedReportRepo) GetByStatus(string) ([]*dbmodels.Report, error) {
	return nil, nil
}

func TestReportEndpointsReturnStoredMetadataUnchanged(t *testing.T) {
	gin.SetMode(gin.TestMode)
	const metadataJSON = `{"article_count": 30, "analysis_mode": "model", "fallback_reason": null,
		"report_plan": {"control_implications": [{"source_ids": [1], "priority": "high"}]},
		"source_articles": [{"title": "Evidence", "cves": []}], "regulatory_bodies": []}`
	var written map[string]any
	if err := json.Unmarshal([]byte(metadataJSON), &written); err != nil {
		t.Fatal(err)
	}
	generatedAt := time.Date(2026, time.August, 13, 12, 0, 0, 0, time.UTC)
	repo := &storedReportRepo{report: &dbmodels.Report{
		ID: "report-123", Status: dbmodels.StatusCompleted, GeneratedAt: &generatedAt,
		Metadata: dbmodels.ReportMetadata(written),
	}}
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	handler := NewReportsHandler(services.NewReportService(repo, nil, nil, logger), logger)
	router := gin.New()
	router.GET("/reports/:id", handler.GetReport)
	router.GET("/reports/:id/status", handler.GetReportStatus)
	router.GET("/reports", handler.ListReports)

	get := func(path string) map[string]any {
		t.Helper()
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, path, nil))
		if recorder.Code != http.StatusOK {
			t.Fatalf("%s returned %d", path, recorder.Code)
		}
		var body map[string]any
		if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
			t.Fatal(err)
		}
		return body
	}

	report := get("/reports/report-123")
	if !reflect.DeepEqual(report["metadata"], written) {
		t.Fatalf("metadata = %#v, want %#v", report["metadata"], written)
	}
	if status := get("/reports/report-123/status"); status["status"] != dbmodels.StatusCompleted || status["id"] != "report-123" {
		t.Fatalf("status = %#v", status)
	}
	summaries := get("/reports")["reports"].([]any)
	if count := summaries[0].(map[string]any)["article_count"]; count != float64(30) {
		t.Fatalf("listed article count = %#v", count)
	}
}
