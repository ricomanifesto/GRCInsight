package middleware

import (
    "strings"
    "github.com/gin-gonic/gin"
)

// CORSMiddleware handles Cross-Origin Resource Sharing with allowed origins
func CORSMiddleware(allowedOrigins []string) gin.HandlerFunc {
    // Normalize allowed origins
    origins := make([]string, 0, len(allowedOrigins))
    allowAll := false
    for _, o := range allowedOrigins {
        o = strings.TrimSpace(o)
        if o == "*" {
            allowAll = true
        }
        if o != "" {
            origins = append(origins, o)
        }
    }

    return func(c *gin.Context) {
        origin := c.Request.Header.Get("Origin")
        allowed := ""
        if allowAll {
            allowed = "*"
        } else {
            for _, o := range origins {
                if o == origin {
                    allowed = origin
                    break
                }
            }
        }

        if allowed != "" {
            c.Header("Access-Control-Allow-Origin", allowed)
            c.Header("Vary", "Origin")
            c.Header("Access-Control-Allow-Credentials", "true")
        }
        c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        c.Header("Access-Control-Expose-Headers", "Content-Length")

        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }

        c.Next()
    }
}
