package handlers

import (
	"errors"
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	dbmodels "grcinsight/internal/database/models"
	"grcinsight/internal/services"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type failingCreateRepo struct{ storedReportRepo }

func (*failingCreateRepo) Create(*dbmodels.Report) error {
	return errors.New("private backend diagnostic: test-resource-id")
}
func TestGenerateReportDoesNotDiscloseBackendErrors(t *testing.T) {
	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	h := NewReportsHandler(services.NewReportService(&failingCreateRepo{}, nil, nil, logger), logger)
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("request_id", "test-request"); c.Next() })
	r.POST("/", h.GenerateReport)
	req := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(`{"feed_url":"https://feed.example.test/rss"}`))
	req.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()
	r.ServeHTTP(response, req)
	if response.Code != 500 {
		t.Fatalf("status=%d", response.Code)
	}
	body := response.Body.String()
	if strings.Contains(body, "private backend") || strings.Contains(body, "test-resource-id") || strings.Contains(body, "details") {
		t.Fatalf("backend detail disclosed: %s", body)
	}
	if !strings.Contains(body, "test-request") {
		t.Fatalf("missing request reference: %s", body)
	}
}

func TestGenerateReportRejectsUnsupportedModelBeforeService(t *testing.T) {
	t.Setenv("LLM_MODEL", "openrouter/server-approved/model")
	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	h := NewReportsHandler(services.NewReportService(&failingCreateRepo{}, nil, nil, logger), logger)
	r := gin.New()
	r.POST("/", h.GenerateReport)
	req := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(`{"feed_url":"https://feed.example.test/rss","config":{"model":"openrouter/other/model"}}`))
	req.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()
	r.ServeHTTP(response, req)
	if response.Code != http.StatusBadRequest {
		t.Fatalf("status=%d want=400", response.Code)
	}
}
