package middleware

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestCORSCredentialPolicy(t *testing.T) {
	gin.SetMode(gin.TestMode)
	for _, tc := range []struct {
		name                       string
		origins                    []string
		origin, allow, credentials string
	}{
		{"default", nil, "https://other.example.test", "", ""},
		{"explicit", []string{"https://app.example.test"}, "https://app.example.test", "https://app.example.test", "true"},
		{"denied", []string{"https://app.example.test"}, "https://other.example.test", "", ""},
		{"wildcard", []string{"*"}, "https://other.example.test", "*", ""},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r := gin.New()
			r.Use(CORSMiddleware(tc.origins))
			r.GET("/", func(c *gin.Context) { c.Status(200) })
			request := httptest.NewRequest(http.MethodOptions, "/", nil)
			request.Header.Set("Origin", tc.origin)
			response := httptest.NewRecorder()
			r.ServeHTTP(response, request)
			if response.Code != 204 || response.Header().Get("Access-Control-Allow-Origin") != tc.allow || response.Header().Get("Access-Control-Allow-Credentials") != tc.credentials {
				t.Fatalf("CORS response: %d %v", response.Code, response.Header())
			}
			if !strings.Contains(response.Header().Get("Access-Control-Allow-Headers"), "X-API-Key") {
				t.Fatal("API key header omitted from preflight")
			}
		})
	}
}
