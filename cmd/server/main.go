package main

import (
	"fmt"
	"log"

	"grcinsight/internal/api/routes"
	"grcinsight/internal/config"
	"grcinsight/internal/database"
	"grcinsight/internal/services"
	"grcinsight/internal/utils"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using system environment variables")
	}

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize logger
	logger := utils.NewLogger(cfg.Logging)
	logger.Info("Starting GRCInsight Go Service")

	// Initialize DynamoDB
	dynamoRepo, err := database.Initialize(cfg.Database, logger)
	if err != nil {
		logger.Fatalf("Failed to initialize database: %v", err)
	}

	// Initialize services
	serviceContainer := services.NewContainer(dynamoRepo, cfg, logger)

	// Set Gin mode
	gin.SetMode(cfg.Server.Mode)

	// Setup router
	router := routes.SetupRouter(serviceContainer, logger)

	// Start server
	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	logger.Infof("Server starting on %s", addr)
	
	if err := router.Run(addr); err != nil {
		logger.Fatalf("Failed to start server: %v", err)
	}
}
