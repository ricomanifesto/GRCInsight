package routes

import (
	"net/http"
	"testing"

	"grcinsight/internal/config"
	"grcinsight/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func TestReportRoutesDoNotExposeDeletion(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := SetupRouter(&services.Container{Config: &config.Config{}}, logrus.New())
	readRoute := false
	for _, route := range router.Routes() {
		if route.Method == http.MethodDelete && route.Path == "/api/v1/reports/:id" {
			t.Fatalf("standalone API exposes deletion route %s", route.Path)
		}
		if route.Method == http.MethodGet && route.Path == "/api/v1/reports/:id" {
			readRoute = true
		}
	}
	if !readRoute {
		t.Fatal("report read route is missing")
	}
}
