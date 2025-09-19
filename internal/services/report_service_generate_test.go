package services

import (
    "testing"
    "time"

    dbmodels "grcinsight/internal/database/models"
    apimodels "grcinsight/internal/models"
)

// fakeReportRepo implements ReportRepository for testing GenerateReport
type fakeReportRepo struct{
    created *dbmodels.Report
    updated *dbmodels.Report
}
func (f *fakeReportRepo) Create(r *dbmodels.Report) error { r.ID = "rep_test"; now := time.Now(); r.CreatedAt = now; r.UpdatedAt = now; f.created = r; return nil }
func (f *fakeReportRepo) GetByID(id string) (*dbmodels.Report, error) { return f.updated, nil }
func (f *fakeReportRepo) List(limit, offset int) ([]*dbmodels.Report, int64, error) { return nil, 0, nil }
func (f *fakeReportRepo) Update(r *dbmodels.Report) error { f.updated = r; return nil }
func (f *fakeReportRepo) Delete(id string) error { return nil }
func (f *fakeReportRepo) GetByStatus(status string) ([]*dbmodels.Report, error) { return nil, nil }

// fakePythonClient implements minimal PythonServiceClient behavior
type fakePythonClient struct{
    resp *apimodels.WorkflowResponse
}
func (f *fakePythonClient) IsAsync() bool { return false }
func (f *fakePythonClient) RunWorkflow(req *apimodels.WorkflowRequest) (*apimodels.WorkflowResponse, error) { return f.resp, nil }
func (f *fakePythonClient) RunWorkflowAsync(req *apimodels.WorkflowRequest, reportID string) error { return nil }
func (f *fakePythonClient) HealthCheck() error { return nil }

// fakeArticleRepo tracks CreateForReport calls
type fakeArticleRepo2 struct{ calls int }
func (f *fakeArticleRepo2) Create(a *dbmodels.Article) error { f.calls++; return nil }
func (f *fakeArticleRepo2) CreateForReport(reportID string, a *dbmodels.Article) error { f.calls++; return nil }
func (f *fakeArticleRepo2) GetByID(id uint) (*dbmodels.Article, error) { return nil, nil }
func (f *fakeArticleRepo2) GetByURL(url string) (*dbmodels.Article, error) { return nil, nil }
func (f *fakeArticleRepo2) List(limit, offset int) ([]*dbmodels.Article, int64, error) { return nil, 0, nil }
func (f *fakeArticleRepo2) Update(a *dbmodels.Article) error { return nil }
func (f *fakeArticleRepo2) Delete(id uint) error { return nil }
func (f *fakeArticleRepo2) GetGRCArticles(limit, offset int) ([]*dbmodels.Article, int64, error) { return nil, 0, nil }
func (f *fakeArticleRepo2) GetByReportID(reportID string, limit, offset int) ([]*dbmodels.Article, int64, error) { return nil, 0, nil }

func TestGenerateReport_PersistsReportAndArticles(t *testing.T) {
    fr := &fakeReportRepo{}
    fa := &fakeArticleRepo2{}
    pc := &fakePythonClient{resp: &apimodels.WorkflowResponse{
        Status: "completed",
        Report: &apimodels.Report{Title: "GRC Report", Content: "Hello", GeneratedAt: time.Now()},
        Metadata: &apimodels.Metadata{ArticleCount: 1, GRCArticleCount: 1},
        Articles: []apimodels.ArticleRecord{{
            Title: "A1", URL: "https://ex.com/1", Source: "Feed", Summary: "S",
            Published: time.Now(), HasGRCContent: true,
            Regulations: []string{"GDPR"}, Frameworks: []string{"ISO 27001"}, Industries: []string{"Tech"}, RegulatoryBodies: []string{"ICO"},
        }},
    }}

    svc := &ReportService{
        reportRepo:   fr,
        articleRepo:  fa,
        pythonClient: pc,
        logger:       nil,
    }

    req := &apimodels.GenerateReportRequest{FeedURL: "https://example.com/rss", Config: apimodels.AnalysisConfig{Model: "gpt-5", MaxTokens: 4000}}
    report, err := svc.GenerateReport(req)
    if err != nil { t.Fatalf("unexpected error: %v", err) }

    if report.Status != dbmodels.StatusCompleted { t.Fatalf("expected completed, got %s", report.Status) }
    if fr.updated == nil || fr.updated.Content == "" { t.Fatalf("report not updated or content missing") }
    if fa.calls == 0 { t.Fatalf("expected articles to be persisted") }
}

