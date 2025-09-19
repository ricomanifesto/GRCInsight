package services

import (
    "os"
    "time"

    "grcinsight/internal/database"
    "grcinsight/internal/database/dynamodb"
    "grcinsight/internal/models"

    "github.com/sirupsen/logrus"
)

// HealthService handles health check operations
type HealthService struct {
	dynamoRepo   *dynamodb.Repository
	pythonClient *PythonServiceClient
	logger       *logrus.Logger
}

// NewHealthService creates a new health service
func NewHealthService(dynamoRepo *dynamodb.Repository, pythonClient *PythonServiceClient, logger *logrus.Logger) *HealthService {
	return &HealthService{
		dynamoRepo:   dynamoRepo,
		pythonClient: pythonClient,
		logger:       logger,
	}
}

// CheckHealth performs a comprehensive health check
func (s *HealthService) CheckHealth() *models.HealthStatus {
    status := &models.HealthStatus{
        Status:    "healthy",
        Timestamp: time.Now(),
        Services:  make(map[string]models.ServiceHealth),
        Version:   getServiceVersion(),
    }

	// Check DynamoDB health
	if err := database.HealthCheck(s.dynamoRepo); err != nil {
		status.Services["dynamodb"] = models.ServiceHealth{
			Status: "unhealthy",
			Error:  err.Error(),
		}
		status.Status = "unhealthy"
		s.logger.WithError(err).Error("DynamoDB health check failed")
	} else {
		status.Services["dynamodb"] = models.ServiceHealth{Status: "healthy"}
	}

	// Check Python service health
	if err := s.pythonClient.HealthCheck(); err != nil {
		status.Services["python_service"] = models.ServiceHealth{
			Status: "unhealthy",
			Error:  err.Error(),
		}
		status.Status = "unhealthy"
		s.logger.WithError(err).Error("Python service health check failed")
	} else {
		status.Services["python_service"] = models.ServiceHealth{Status: "healthy"}
	}

	return status
}

func getServiceVersion() string {
    if v := os.Getenv("SERVICE_VERSION"); v != "" {
        return v
    }
    return "1.0.0"
}

// CheckDatabase checks only the DynamoDB health
func (s *HealthService) CheckDatabase() error {
	return database.HealthCheck(s.dynamoRepo)
}

// CheckPythonService checks only the Python service health
func (s *HealthService) CheckPythonService() error {
	return s.pythonClient.HealthCheck()
}
