package middleware

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func TestRecoveryDoesNotDumpAPIKeyHeaders(t *testing.T) {
	beforeMode := gin.Mode()
	gin.SetMode(gin.DebugMode)
	t.Cleanup(func() { gin.SetMode(beforeMode) })
	var frameworkLogs, structuredLogs bytes.Buffer
	previous := gin.DefaultErrorWriter
	gin.DefaultErrorWriter = &frameworkLogs
	t.Cleanup(func() { gin.DefaultErrorWriter = previous })
	logger := logrus.New()
	logger.SetOutput(&structuredLogs)
	router := gin.New()
	router.Use(RecoveryMiddleware(logger), APIKeyMiddleware("synthetic-key-never-log"))
	router.GET("/", func(*gin.Context) { panic("synthetic handler failure") })
	request := httptest.NewRequest(http.MethodGet, "/", nil)
	request.Header.Set("X-API-Key", "synthetic-key-never-log")
	response := httptest.NewRecorder()
	router.ServeHTTP(response, request)
	if response.Code != 500 {
		t.Fatalf("status=%d", response.Code)
	}
	if strings.Contains(frameworkLogs.String()+structuredLogs.String(), "synthetic-key-never-log") {
		t.Fatal("recovery disclosed the API credential")
	}
	if !strings.Contains(structuredLogs.String(), "Panic recovered") {
		t.Fatal("structured diagnostic missing")
	}
}
