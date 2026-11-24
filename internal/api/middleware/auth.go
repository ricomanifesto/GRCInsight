package middleware

import (
	"crypto/sha256"
	"crypto/subtle"
	"net/http"

	"github.com/gin-gonic/gin"
)

// APIKeyMiddleware authenticates sensitive HTTP routes and fails closed when
// operators have not configured the shared server credential.
func APIKeyMiddleware(key string) gin.HandlerFunc {
	expected := sha256.Sum256([]byte(key))
	return func(c *gin.Context) {
		if key == "" {
			c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": "API authentication is not configured"})
			return
		}
		supplied := sha256.Sum256([]byte(c.GetHeader("X-API-Key")))
		if subtle.ConstantTimeCompare(expected[:], supplied[:]) != 1 {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid API key"})
			return
		}
		c.Next()
	}
}
