package handlers

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func TestGenerateReport_InvalidBody_Returns400(t *testing.T) {
	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	h := &ReportsHandler{reportService: nil, logger: logger}

	r := gin.New()
	r.POST("/api/v1/reports/generate", h.GenerateReport)

	w := httptest.NewRecorder()
	// Send invalid JSON
	req, _ := http.NewRequest("POST", "/api/v1/reports/generate", strings.NewReader("{invalid"))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestGenerateReportInvalidOutputReturns400BeforeService(t *testing.T) {
	gin.SetMode(gin.TestMode)
	for _, cap := range []string{"0", "-1", "16001", "true", "false", "8000.0", `"8000"`, "null"} {
		t.Run(cap, func(t *testing.T) {
			logger := logrus.New()
			logger.SetOutput(io.Discard)
			h := &ReportsHandler{reportService: nil, logger: logger}
			router := gin.New()
			router.POST("/api/v1/reports/generate", h.GenerateReport)
			body := `{"feed_url":"https://feed.example.test/rss","config":{"max_tokens":` + cap + `}}`
			request := httptest.NewRequest(http.MethodPost, "/api/v1/reports/generate", strings.NewReader(body))
			request.Header.Set("Content-Type", "application/json")
			response := httptest.NewRecorder()
			router.ServeHTTP(response, request)
			if response.Code != http.StatusBadRequest {
				t.Fatalf("status %d, want 400", response.Code)
			}
		})
	}
}
