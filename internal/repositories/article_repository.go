package repositories

import (
    "context"
    "hash/fnv"
    "time"

    "grcinsight/internal/database/dynamodb"
    "grcinsight/internal/database/models"
)

// articleRepository implements ArticleRepository interface using DynamoDB
type articleRepository struct {
    repo *dynamodb.Repository
}

// NewArticleRepository creates a new DynamoDB-based article repository
func NewArticleRepository(repo *dynamodb.Repository) ArticleRepository {
    return &articleRepository{repo: repo}
}

// Create creates a new article (idempotent by URL)
func (r *articleRepository) Create(article *models.Article) error {
    ctx := context.Background()
    // Derive a stable numeric ID from URL (FNV-1a)
    nid := hashURL(article.URL)
    artID := formatArticleID(nid)

    dArt := &dynamodb.Article{
        ArticleID:     artID,
        NumericID:     nid,
        ReportID:      "",
        Title:         article.Title,
        URL:           article.URL,
        Content:       article.Content,
        Summary:       article.Summary,
        Source:        article.Source,
        Published:     article.Published.UTC().Format(time.RFC3339),
        CreatedAt:     dynamodb.ToISO8601(time.Now()),
        UpdatedAt:     dynamodb.ToISO8601(time.Now()),
        HasGRCContent: article.HasGRCContent,
        Regulations:   article.Regulations,
        Frameworks:    article.Frameworks,
        Industries:    article.Industries,
        RegulatoryBodies: article.RegulatoryBodies,
    }
    if err := r.repo.CreateArticle(ctx, dArt); err != nil {
        return err
    }
    // Set derived numeric ID back on model
    article.ID = uint(nid)
    return nil
}

// CreateForReport creates a new article associated with a report
func (r *articleRepository) CreateForReport(reportID string, article *models.Article) error {
    ctx := context.Background()
    nid := hashURL(article.URL)
    artID := formatArticleID(nid)
    dArt := &dynamodb.Article{
        ArticleID:     artID,
        NumericID:     nid,
        ReportID:      reportID,
        Title:         article.Title,
        URL:           article.URL,
        Content:       article.Content,
        Summary:       article.Summary,
        Source:        article.Source,
        Published:     article.Published.UTC().Format(time.RFC3339),
        CreatedAt:     dynamodb.ToISO8601(time.Now()),
        UpdatedAt:     dynamodb.ToISO8601(time.Now()),
        HasGRCContent: article.HasGRCContent,
        Regulations:   article.Regulations,
        Frameworks:    article.Frameworks,
        Industries:    article.Industries,
        RegulatoryBodies: article.RegulatoryBodies,
    }
    if err := r.repo.CreateArticle(ctx, dArt); err != nil {
        return err
    }
    article.ID = uint(nid)
    return nil
}

// GetByID retrieves an article by numeric ID (hash)
func (r *articleRepository) GetByID(id uint) (*models.Article, error) {
    ctx := context.Background()
    dArt, err := r.repo.GetArticleByNumericID(ctx, uint32(id))
    if err != nil {
        return nil, err
    }
    return convertDynamoArticle(dArt), nil
}

// GetByURL retrieves an article by URL
func (r *articleRepository) GetByURL(url string) (*models.Article, error) {
    ctx := context.Background()
    dArt, err := r.repo.GetArticleByURL(ctx, url)
    if err != nil {
        return nil, err
    }
    return convertDynamoArticle(dArt), nil
}

// List retrieves articles with naive pagination
func (r *articleRepository) List(limit, offset int) ([]*models.Article, int64, error) {
    ctx := context.Background()
    dArts, err := r.repo.ListArticles(ctx, int32(limit), int32(offset))
    if err != nil {
        return nil, 0, err
    }
    out := make([]*models.Article, 0, len(dArts))
    for _, a := range dArts {
        aa := a // copy
        out = append(out, convertDynamoArticle(&aa))
    }
    total := int64(len(out))
    return out, total, nil
}

// Update updates an existing article
func (r *articleRepository) Update(article *models.Article) error {
    ctx := context.Background()
    dArt := &dynamodb.Article{
        ArticleID:     formatArticleID(uint32(article.ID)),
        NumericID:     uint32(article.ID),
        Title:         article.Title,
        URL:           article.URL,
        Content:       article.Content,
        Summary:       article.Summary,
        Source:        article.Source,
        Published:     article.Published.UTC().Format(time.RFC3339),
        HasGRCContent: article.HasGRCContent,
        Regulations:   article.Regulations,
        Frameworks:    article.Frameworks,
        Industries:    article.Industries,
        RegulatoryBodies: article.RegulatoryBodies,
    }
    return r.repo.UpdateArticle(ctx, dArt)
}

// Delete deletes an article
func (r *articleRepository) Delete(id uint) error {
    ctx := context.Background()
    return r.repo.DeleteArticle(ctx, formatArticleID(uint32(id)))
}

// GetGRCArticles retrieves articles that contain GRC content
func (r *articleRepository) GetGRCArticles(limit, offset int) ([]*models.Article, int64, error) {
    ctx := context.Background()
    dArts, err := r.repo.GetGRCArticles(ctx, int32(limit), int32(offset))
    if err != nil {
        return nil, 0, err
    }
    out := make([]*models.Article, 0, len(dArts))
    for _, a := range dArts {
        aa := a
        out = append(out, convertDynamoArticle(&aa))
    }
    total := int64(len(out))
    return out, total, nil
}

// GetByReportID retrieves articles by associated report id
func (r *articleRepository) GetByReportID(reportID string, limit, offset int) ([]*models.Article, int64, error) {
    ctx := context.Background()
    dArts, err := r.repo.GetArticlesByReportID(ctx, reportID, int32(limit), int32(offset))
    if err != nil {
        return nil, 0, err
    }
    out := make([]*models.Article, 0, len(dArts))
    for _, a := range dArts {
        aa := a
        out = append(out, convertDynamoArticle(&aa))
    }
    total := int64(len(out))
    return out, total, nil
}

// Helpers
func hashURL(url string) uint32 {
    h := fnv.New32a()
    _, _ = h.Write([]byte(url))
    return h.Sum32()
}

func formatArticleID(n uint32) string {
    return "a_" + time.Now().Format("20060102") + "_" + toHex8(n)
}

func toHex8(n uint32) string {
    const hex = "0123456789abcdef"
    b := make([]byte, 8)
    for i := 7; i >= 0; i-- {
        b[i] = hex[n&0xF]
        n >>= 4
    }
    return string(b)
}

func convertDynamoArticle(a *dynamodb.Article) *models.Article {
    // Parse times
    pub := time.Now()
    if t, err := time.Parse(time.RFC3339, a.Published); err == nil {
        pub = t
    }
    created := time.Now()
    if t, err := dynamodb.FromISO8601(a.CreatedAt); err == nil {
        created = t
    }
    updated := time.Now()
    if t, err := dynamodb.FromISO8601(a.UpdatedAt); err == nil {
        updated = t
    }
    return &models.Article{
        ID:            uint(a.NumericID),
        Title:         a.Title,
        URL:           a.URL,
        Content:       a.Content,
        Summary:       a.Summary,
        Source:        a.Source,
        Published:     pub,
        CreatedAt:     created,
        UpdatedAt:     updated,
        HasGRCContent: a.HasGRCContent,
        Regulations:   a.Regulations,
        Frameworks:    a.Frameworks,
        Industries:    a.Industries,
        RegulatoryBodies: a.RegulatoryBodies,
    }
}
