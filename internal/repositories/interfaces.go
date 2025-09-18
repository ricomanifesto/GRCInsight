package repositories

import (
	"grcinsight/internal/database/models"
)

// ReportRepository defines the interface for report data access
type ReportRepository interface {
    Create(report *models.Report) error
    GetByID(id string) (*models.Report, error)
    List(limit, offset int) ([]*models.Report, int64, error)
    Update(report *models.Report) error
    Delete(id string) error
    GetByStatus(status string) ([]*models.Report, error)
}

// ArticleRepository defines the interface for article data access
type ArticleRepository interface {
	Create(article *models.Article) error
	GetByID(id uint) (*models.Article, error)
	GetByURL(url string) (*models.Article, error)
	List(limit, offset int) ([]*models.Article, int64, error)
	Update(article *models.Article) error
	Delete(id uint) error
	GetGRCArticles(limit, offset int) ([]*models.Article, int64, error)
}
