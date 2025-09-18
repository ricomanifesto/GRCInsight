package dynamodb

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/sirupsen/logrus"
)

// ClientConfig holds configuration for DynamoDB client
type ClientConfig struct {
	Region   string
	Endpoint string // Optional: for local DynamoDB
}

// Initialize creates a new DynamoDB client and repository
func Initialize(ctx context.Context, cfg ClientConfig, logger *logrus.Logger) (*Repository, error) {
	// Load AWS configuration
	awsCfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion(cfg.Region),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	// Create DynamoDB client
	var client *dynamodb.Client
	if cfg.Endpoint != "" {
		// Use custom endpoint (for local DynamoDB)
		client = dynamodb.NewFromConfig(awsCfg, func(o *dynamodb.Options) {
			o.BaseEndpoint = aws.String(cfg.Endpoint)
		})
		logger.WithField("endpoint", cfg.Endpoint).Info("Using custom DynamoDB endpoint")
	} else {
		// Use default AWS DynamoDB
		client = dynamodb.NewFromConfig(awsCfg)
		logger.WithField("region", cfg.Region).Info("Using AWS DynamoDB")
	}

	// Create repository
	repo := NewRepository(client, logger)

	// Verify connection with health check
	if err := repo.HealthCheck(ctx); err != nil {
		return nil, fmt.Errorf("DynamoDB health check failed: %w", err)
	}

	logger.Info("DynamoDB initialized successfully")
	return repo, nil
}

// InitializeForLambda creates a DynamoDB repository optimized for Lambda environment
func InitializeForLambda(ctx context.Context, logger *logrus.Logger) (*Repository, error) {
	// In Lambda, AWS SDK automatically uses IAM role credentials
	// and region from environment variables
	cfg := ClientConfig{
		Region: "us-east-1", // Default region, can be overridden by AWS_REGION env var
	}

	return Initialize(ctx, cfg, logger)
}