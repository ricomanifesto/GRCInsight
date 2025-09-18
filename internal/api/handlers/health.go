package handlers

import (
	"net/http"

	"grcinsight/internal/services"

	"github.com/gin-gonic/gin"
)

// HealthHandler handles health check endpoints
type HealthHandler struct {
	healthService *services.HealthService
}

// NewHealthHandler creates a new health handler
func NewHealthHandler(healthService *services.HealthService) *HealthHandler {
	return &HealthHandler{
		healthService: healthService,
	}
}

// HealthCheck performs a comprehensive health check
func (h *HealthHandler) HealthCheck(c *gin.Context) {
	health := h.healthService.CheckHealth()
	
	statusCode := http.StatusOK
	if health.Status != "healthy" {
		statusCode = http.StatusServiceUnavailable
	}
	
	c.JSON(statusCode, health)
}

// DatabaseHealthCheck checks database health only
func (h *HealthHandler) DatabaseHealthCheck(c *gin.Context) {
	if err := h.healthService.CheckDatabase(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status": "unhealthy",
			"error":  err.Error(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"status": "healthy",
	})
}

// PythonServiceHealthCheck checks Python service health only
func (h *HealthHandler) PythonServiceHealthCheck(c *gin.Context) {
	if err := h.healthService.CheckPythonService(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status": "unhealthy",
			"error":  err.Error(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"status": "healthy",
	})
}