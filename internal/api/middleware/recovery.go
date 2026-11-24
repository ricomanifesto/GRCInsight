package middleware

import (
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// RecoveryMiddleware creates a custom recovery middleware with structured logging
func RecoveryMiddleware(logger *logrus.Logger) gin.HandlerFunc {
	// Gin's default recovery logger dumps request headers in debug mode.
	// Keep diagnostics in the structured callback without recording credentials.
	return gin.CustomRecoveryWithWriter(io.Discard, func(c *gin.Context, recovered interface{}) {
		logger.WithFields(logrus.Fields{
			"panic":      recovered,
			"path":       c.Request.URL.Path,
			"method":     c.Request.Method,
			"client_ip":  c.ClientIP(),
			"user_agent": c.Request.UserAgent(),
		}).Error("Panic recovered")

		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Internal server error",
		})
	})
}
