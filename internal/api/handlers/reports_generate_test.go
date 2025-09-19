package handlers

import (
    "net/http"
    "net/http/httptest"
    "strings"
    "testing"

    "github.com/gin-gonic/gin"
)

func TestGenerateReport_InvalidBody_Returns400(t *testing.T) {
    gin.SetMode(gin.TestMode)
    h := &ReportsHandler{reportService: nil, logger: nil}

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

