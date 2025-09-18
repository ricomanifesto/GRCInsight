package main

import (
	"context"
	"log"
	"os"

	"grcinsight/internal/api/routes"
	"grcinsight/internal/config"
	"grcinsight/internal/database"
	"grcinsight/internal/services"
	"grcinsight/internal/utils"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/awslabs/aws-lambda-go-api-proxy/gin"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/sirupsen/logrus"
)

var ginLambda *ginadapter.GinLambda

func init() {
	// Load environment variables (Lambda will set these)
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using Lambda environment variables")
	}

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize logger
	logger := utils.NewLogger(cfg.Logging)
    logger.WithFields(logrus.Fields{
        "aws_lambda":                os.Getenv("AWS_LAMBDA_FUNCTION_NAME") != "",
        "python_lambda_function_name": os.Getenv("PYTHON_LAMBDA_FUNCTION_NAME"),
    }).Info("Starting GRCInsight Lambda Service")

	// Initialize DynamoDB for Lambda
	dynamoRepo, err := database.InitializeForLambda(logger)
	if err != nil {
		logger.Fatalf("Failed to initialize database: %v", err)
	}

	// Initialize services
	serviceContainer := services.NewContainer(dynamoRepo, cfg, logger)

	// Set Gin mode (use release for Lambda)
	if os.Getenv("AWS_LAMBDA_FUNCTION_NAME") != "" {
		gin.SetMode(gin.ReleaseMode)
	} else {
		gin.SetMode(cfg.Server.Mode)
	}

	// Setup router (same as regular server)
	router := routes.SetupRouter(serviceContainer, logger)

	// Initialize Gin Lambda adapter
	ginLambda = ginadapter.New(router)

	logger.Info("Lambda service initialized successfully")
}

// Handler is the main Lambda function handler
func Handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// Use the Gin Lambda adapter to handle the request
	return ginLambda.ProxyWithContext(ctx, req)
}

func main() {
	// Start Lambda function
	lambda.Start(Handler)
}
