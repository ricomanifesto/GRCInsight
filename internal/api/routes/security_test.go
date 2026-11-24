package routes

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	awsddb "github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"grcinsight/internal/config"
	db "grcinsight/internal/database/dynamodb"
	"grcinsight/internal/services"

	"github.com/aws/aws-lambda-go/events"
	ginadapter "github.com/awslabs/aws-lambda-go-api-proxy/gin"
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func securityRouter(key string) *gin.Engine {
	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	return SetupRouter(&services.Container{Config: &config.Config{Auth: config.AuthConfig{APIKey: key}}}, logger)
}

func TestSensitiveReportRoutesRequireAPIKey(t *testing.T) {
	for _, path := range []string{"/api/v1/reports", "/api/v1/reports/r", "/api/v1/reports/r/status", "/api/v1/reports/r/articles", "/api/v1/reports/generate"} {
		for _, supplied := range []string{"", "wrong"} {
			method := http.MethodGet
			if strings.HasSuffix(path, "generate") {
				method = http.MethodPost
			}
			req := httptest.NewRequest(method, path, strings.NewReader("{}"))
			req.Header.Set("X-API-Key", supplied)
			rec := httptest.NewRecorder()
			securityRouter("test-secret").ServeHTTP(rec, req)
			if rec.Code != http.StatusUnauthorized {
				t.Errorf("%s key=%q: status=%d, want 401", path, supplied, rec.Code)
			}
		}
	}
}

func TestReportAPIKeyFailsClosedAndAcceptsConfiguredKey(t *testing.T) {
	for _, tc := range []struct {
		name, key, supplied string
		want                int
	}{
		{"unconfigured", "", "", http.StatusServiceUnavailable},
		{"unconfigured with credential", "", "test-secret", http.StatusServiceUnavailable},
		{"configured", "test-secret", "test-secret", http.StatusBadRequest},
	} {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/api/v1/reports/generate", strings.NewReader("{invalid"))
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("X-API-Key", tc.supplied)
			rec := httptest.NewRecorder()
			securityRouter(tc.key).ServeHTTP(rec, req)
			if rec.Code != tc.want {
				t.Fatalf("status=%d want=%d", rec.Code, tc.want)
			}
		})
	}
}

func TestLambdaAdapterEnforcesReportAPIKey(t *testing.T) {
	adapter := ginadapter.New(securityRouter("test-secret"))
	for _, tc := range []struct {
		key  string
		want int
	}{{"", 401}, {"wrong", 401}, {"test-secret", 400}} {
		response, err := adapter.ProxyWithContext(context.Background(), events.APIGatewayProxyRequest{HTTPMethod: "POST", Path: "/api/v1/reports/generate", Headers: map[string]string{"X-API-Key": tc.key, "Content-Type": "application/json"}, Body: "{invalid"})
		if err != nil || response.StatusCode != tc.want {
			t.Fatalf("key=%q status=%d err=%v", tc.key, response.StatusCode, err)
		}
	}
}

type healthyDB struct{ db.API }

func (healthyDB) DescribeTable(context.Context, *awsddb.DescribeTableInput, ...func(*awsddb.Options)) (*awsddb.DescribeTableOutput, error) {
	return &awsddb.DescribeTableOutput{}, nil
}

func TestPublicRoutesRemainPublic(t *testing.T) {
	t.Setenv("PYTHON_LAMBDA_FUNCTION_NAME", "")
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	}))
	defer upstream.Close()
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	cfg := &config.Config{PythonService: config.PythonServiceConfig{URL: upstream.URL}}
	container := services.NewContainer(db.NewRepository(healthyDB{}, logger), cfg, logger)
	router := SetupRouter(container, logger)
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "site/static"), 0700); err != nil {
		t.Fatal(err)
	}
	for path, contents := range map[string]string{"site/index.html": "public site", "site/static/theme.css": "public asset"} {
		if err := os.WriteFile(filepath.Join(root, path), []byte(contents), 0600); err != nil {
			t.Fatal(err)
		}
	}
	before, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(before) })
	for _, path := range []string{"/", "/static/theme.css", "/health", "/health/database", "/health/python", "/api/v1/version"} {
		response := httptest.NewRecorder()
		router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, path, nil))
		if response.Code != http.StatusOK {
			t.Fatalf("public %s failed: %d %s", path, response.Code, response.Body.String())
		}
	}
}
