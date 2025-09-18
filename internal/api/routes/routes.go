package routes

import (
	"grcinsight/internal/api/handlers"
	"grcinsight/internal/api/middleware"
	"grcinsight/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// SetupRouter configures and returns the main router
func SetupRouter(container *services.Container, logger *logrus.Logger) *gin.Engine {
	router := gin.New()

	// Global middleware
	router.Use(middleware.RecoveryMiddleware(logger))
	router.Use(middleware.LoggingMiddleware(logger))
	router.Use(middleware.CORSMiddleware())
	router.Use(middleware.RequestIDMiddleware())

	// Initialize handlers
	healthHandler := handlers.NewHealthHandler(container.HealthService)
	reportsHandler := handlers.NewReportsHandler(container.ReportService, logger)
	staticHandler := handlers.NewStaticHandler()

	// Health check routes
	router.GET("/health", healthHandler.HealthCheck)
	router.GET("/health/database", healthHandler.DatabaseHealthCheck)
	router.GET("/health/python", healthHandler.PythonServiceHealthCheck)

	// API routes
	api := router.Group("/api/v1")
	{
		// Report management
		reports := api.Group("/reports")
		{
			reports.GET("", reportsHandler.ListReports)
			reports.POST("/generate", reportsHandler.GenerateReport)
			reports.GET("/:id", reportsHandler.GetReport)
			reports.DELETE("/:id", reportsHandler.DeleteReport)
			reports.GET("/:id/status", reportsHandler.GetReportStatus)
		}

		// Configuration endpoints (future)
		config := api.Group("/config")
		{
			config.GET("", func(c *gin.Context) {
				c.JSON(200, gin.H{"message": "Config endpoints coming soon"})
			})
		}

		// System info
		api.GET("/version", func(c *gin.Context) {
			c.JSON(200, gin.H{
				"version": "1.0.0",
				"service": "grcinsight-go",
			})
		})
	}

	// Static file routes
	router.GET("/", staticHandler.ServeIndex)
	router.GET("/static/*filepath", staticHandler.ServeStatic)
	router.GET("/reports/*filepath", staticHandler.ServeReport)

	return router
}