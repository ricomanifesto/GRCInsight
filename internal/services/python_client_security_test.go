package services

import (
	"github.com/sirupsen/logrus"
	"grcinsight/internal/config"
	"grcinsight/internal/models"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestHTTPWorkflowsForwardAPIKeyAndInternalCompletionCredential(t *testing.T) {
	t.Setenv("API_KEY", "api-test-secret")
	t.Setenv("GRC_INTERNAL_TOKEN", "completion-test-secret")
	t.Setenv("PYTHON_LAMBDA_FUNCTION_NAME", "")
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	client := NewPythonServiceClient(config.PythonServiceConfig{URL: "http://python.example.test", Timeout: time.Second}, logger)
	client.httpClient.Transport = roundTripFunc(func(req *http.Request) (*http.Response, error) {
		if req.Header.Get("X-API-Key") != "api-test-secret" {
			t.Error("workflow request missing API key")
		}
		response := `{"status":"completed"}`
		if strings.Contains(req.URL.Path, "/reports/") {
			if req.Header.Get(internalTokenHeader) != "completion-test-secret" {
				t.Error("report completion credential missing")
			}
			response = `{"decision":"committed"}`
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(response)), Header: make(http.Header), Request: req}, nil
	})
	request := &models.WorkflowRequest{FeedURL: "https://feed.example.test/rss"}
	if _, err := client.RunWorkflow(request); err != nil {
		t.Fatal(err)
	}
	if err := client.RunWorkflowForReport(request, WorkflowJob{ReportID: "r", JobID: "j"}); err != nil {
		t.Fatal(err)
	}
}

func TestHTTPWorkflowCredentialsNeverFollowRedirects(t *testing.T) {
	t.Setenv("API_KEY", "api-test-secret")
	t.Setenv("GRC_INTERNAL_TOKEN", "completion-test-secret")
	t.Setenv("PYTHON_LAMBDA_FUNCTION_NAME", "")
	for _, status := range []int{301, 302, 303, 307, 308} {
		for _, report := range []bool{false, true} {
			logger := logrus.New()
			logger.SetOutput(io.Discard)
			client := NewPythonServiceClient(config.PythonServiceConfig{URL: "http://python.example.test", Timeout: time.Second}, logger)
			calls := 0
			client.httpClient.Transport = roundTripFunc(func(req *http.Request) (*http.Response, error) {
				calls++
				if req.URL.Host != "python.example.test" {
					t.Error("redirect crossed the configured service origin")
				}
				header := make(http.Header)
				header.Set("Location", "http://other.example.test/safe")
				code := status
				if calls > 1 {
					code = 200
				}
				return &http.Response{StatusCode: code, Body: io.NopCloser(strings.NewReader(`{"decision":"committed","status":"completed"}`)), Header: header, Request: req}, nil
			})
			request := &models.WorkflowRequest{FeedURL: "https://feed.example.test/rss"}
			var err error
			if report {
				err = client.RunWorkflowForReport(request, WorkflowJob{ReportID: "r", JobID: "j"})
			} else {
				_, err = client.RunWorkflow(request)
			}
			if err == nil || calls != 1 {
				t.Errorf("redirect status=%d report=%t calls=%d err=%v", status, report, calls, err)
			}
		}
	}
}
