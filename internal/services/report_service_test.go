package services

import (
    "testing"
    "time"

    dbmodels "grcinsight/internal/database/models"
    apimodels "grcinsight/internal/models"
)

// fakeArticleRepo implements ArticleRepository for testing
type fakeArticleRepo struct{
    items []*dbmodels.Article
}

func (f *fakeArticleRepo) Create(article *dbmodels.Article) error { f.items = append(f.items, article); return nil }
func (f *fakeArticleRepo) CreateForReport(reportID string, article *dbmodels.Article) error { return f.Create(article) }
func (f *fakeArticleRepo) GetByID(id uint) (*dbmodels.Article, error) { return nil, nil }
func (f *fakeArticleRepo) GetByURL(url string) (*dbmodels.Article, error) { return nil, nil }
func (f *fakeArticleRepo) List(limit, offset int) ([]*dbmodels.Article, int64, error) { return nil, 0, nil }
func (f *fakeArticleRepo) Update(article *dbmodels.Article) error { return nil }
func (f *fakeArticleRepo) Delete(id uint) error { return nil }
func (f *fakeArticleRepo) GetGRCArticles(limit, offset int) ([]*dbmodels.Article, int64, error) { return nil, 0, nil }
func (f *fakeArticleRepo) GetByReportID(reportID string, limit, offset int) ([]*dbmodels.Article, int64, error) {
    return f.items, int64(len(f.items)), nil
}

func TestListReportArticles_MapsRegulatoryBodies(t *testing.T) {
    repo := &fakeArticleRepo{items: []*dbmodels.Article{
        {
            Title: "A1", URL: "https://ex.com/1", Source: "Feed", Summary: "S1",
            Published: time.Now(), HasGRCContent: true,
            Regulations: []string{"GDPR"}, Frameworks: []string{"ISO 27001"}, Industries: []string{"Technology"},
            RegulatoryBodies: []string{"ICO", "CNIL"},
        },
    }}

    svc := &ReportService{
        reportRepo:   nil,
        articleRepo:  repo,
        pythonClient: nil,
        logger:       nil,
    }

    resp, err := svc.ListReportArticles("report_1", 1, 10)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if len(resp.Articles) != 1 {
        t.Fatalf("expected 1 article, got %d", len(resp.Articles))
    }
    a := resp.Articles[0]
    if a.Title != "A1" {
        t.Errorf("wrong title: %s", a.Title)
    }
    wantBodies := []string{"ICO", "CNIL"}
    if len(a.RegulatoryBodies) != len(wantBodies) {
        t.Fatalf("expected %d regulatory bodies, got %d", len(wantBodies), len(a.RegulatoryBodies))
    }
    for i, b := range wantBodies {
        if a.RegulatoryBodies[i] != b {
            t.Errorf("regulatory_bodies[%d]=%s, want %s", i, a.RegulatoryBodies[i], b)
        }
    }

    // Sanity check types for mapping to API model
    _ = apimodels.ArticleRecord{}
}

