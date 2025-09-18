package database

import (
	"context"
	"fmt"

	"grcinsight/internal/config"
	"grcinsight/internal/database/dynamodb"

	"github.com/sirupsen/logrus"
)

// Initialize sets up the DynamoDB connection
func Initialize(cfg config.DatabaseConfig, log *logrus.Logger) (*dynamodb.Repository, error) {
	ctx := context.Background()

	// Use DynamoDB configuration
	dynamoConfig := dynamodb.ClientConfig{
		Region:   cfg.Region,
		Endpoint: cfg.Endpoint,
	}

	repo, err := dynamodb.Initialize(ctx, dynamoConfig, log)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize DynamoDB: %w", err)
	}

	log.Info("DynamoDB initialized successfully")
	return repo, nil
}

// InitializeForLambda sets up DynamoDB connection optimized for Lambda
func InitializeForLambda(log *logrus.Logger) (*dynamodb.Repository, error) {
	ctx := context.Background()

	repo, err := dynamodb.InitializeForLambda(ctx, log)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize DynamoDB for Lambda: %w", err)
	}

	log.Info("DynamoDB initialized for Lambda successfully")
	return repo, nil
}

// HealthCheck checks if the DynamoDB connection is healthy
func HealthCheck(repo *dynamodb.Repository) error {
	ctx := context.Background()
	return repo.HealthCheck(ctx)
}