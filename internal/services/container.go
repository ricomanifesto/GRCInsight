package services

import (
	"grcinsight/internal/config"
	"grcinsight/internal/database/dynamodb"
	"grcinsight/internal/repositories"

	"github.com/sirupsen/logrus"
)

// Container holds all services and their dependencies
type Container struct {
	// Repositories
	ReportRepository  repositories.ReportRepository
	ArticleRepository repositories.ArticleRepository

	// Services
	ReportService  *ReportService
	PythonClient   *PythonServiceClient
	HealthService  *HealthService

	// Configuration and utilities
	Config         *config.Config
	Logger         *logrus.Logger
	DynamoDBRepo   *dynamodb.Repository
}

// NewContainer creates a new service container with all dependencies
func NewContainer(dynamoRepo *dynamodb.Repository, cfg *config.Config, logger *logrus.Logger) *Container {
	// Initialize repositories
	reportRepo := repositories.NewReportRepository(dynamoRepo)
    articleRepo := repositories.NewArticleRepository(dynamoRepo)

	// Initialize Python service client
	pythonClient := NewPythonServiceClient(cfg.PythonService, logger)

	// Initialize services
	reportService := NewReportService(reportRepo, articleRepo, pythonClient, logger)
	healthService := NewHealthService(dynamoRepo, pythonClient, logger)

	return &Container{
		// Repositories
		ReportRepository:  reportRepo,
		ArticleRepository: articleRepo,

		// Services
		ReportService: reportService,
		PythonClient:  pythonClient,
		HealthService: healthService,

		// Configuration and utilities
		Config:       cfg,
		Logger:       logger,
		DynamoDBRepo: dynamoRepo,
	}
}
