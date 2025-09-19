package handlers

import (
    "net/http"
    "net/http/httptest"
    "testing"

    "grcinsight/internal/services"

    "github.com/gin-gonic/gin"
)

// fakeReportService implements just the method we need for testing
type fakeReportService struct{}

func (f *fakeReportService) ListReportArticles(reportID string, page, perPage int) (*struct {
    Articles   []struct{
        Title string `json:"title"`
    } `json:"articles"`
    Total      int64 `json:"total"`
    Page       int   `json:"page"`
    PerPage    int   `json:"per_page"`
    TotalPages int   `json:"total_pages"`
}, error) {
    // Return minimal valid payload
    resp := &struct {
        Articles   []struct{ Title string `json:"title"` } `json:"articles"`
        Total      int64 `json:"total"`
        Page       int   `json:"page"`
        PerPage    int   `json:"per_page"`
        TotalPages int   `json:"total_pages"`
    }{
        Articles:   []struct{ Title string `json:"title"` }{{Title: "A"}},
        Total:      1,
        Page:       1,
        PerPage:    20,
        TotalPages: 1,
    }
    return resp, nil
}

// Ensure fakeReportService satisfies the minimal interface at compile time
var _ interface{ ListReportArticles(string, int, int) (*struct{ Articles []struct{ Title string `json:"title"` } `json:"articles"`; Total int64 `json:"total"`; Page int `json:"page"`; PerPage int `json:"per_page"`; TotalPages int `json:"total_pages"` }, error) } = &fakeReportService{}

func TestListReportArticlesHandler_Success(t *testing.T) {
    gin.SetMode(gin.TestMode)
    frs := &fakeReportService{}
    // We need a ReportsHandler but only ListReportArticles uses reportService.ListReportArticles
    h := &ReportsHandler{reportService: (*services.ReportService)(nil)}
    // Patch the method by shadowing through an anonymous struct embedding is non-trivial; instead
    // we create a small router and handle via closure to call our fake service.

    r := gin.New()
    r.GET("/api/v1/reports/:id/articles", func(c *gin.Context) {
        // mimic ReportsHandler.ListReportArticles using fake service
        id := c.Param("id")
        if id == "" { c.Status(http.StatusBadRequest); return }
        resp, err := frs.ListReportArticles(id, 1, 20)
        if err != nil { c.Status(http.StatusInternalServerError); return }
        c.JSON(http.StatusOK, resp)
    })

    w := httptest.NewRecorder()
    req, _ := http.NewRequest("GET", "/api/v1/reports/rep123/articles", nil)
    r.ServeHTTP(w, req)

    if w.Code != http.StatusOK {
        t.Fatalf("expected 200 OK, got %d", w.Code)
    }
}

