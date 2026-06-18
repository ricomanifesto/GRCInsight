package services

import (
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	"grcinsight/internal/models"

	"github.com/sirupsen/logrus"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (fn roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return fn(req)
}

func TestAnalyzeArticlesRedactsErrorResponseBody(t *testing.T) {
	client := &PythonServiceClient{
		httpClient: &http.Client{
			Timeout: time.Second,
			Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
				return &http.Response{
					StatusCode: http.StatusInternalServerError,
					Body:       io.NopCloser(strings.NewReader("secret upstream payload")),
					Header:     make(http.Header),
					Request:    req,
				}, nil
			}),
		},
		baseURL: "http://python-service.test",
		logger:  logrus.New(),
	}

	_, err := client.AnalyzeArticles(&models.AnalysisRequest{})
	if err == nil {
		t.Fatal("expected AnalyzeArticles to return an error")
	}

	message := err.Error()
	if !strings.Contains(message, "python service returned 500") {
		t.Fatalf("expected status code in error, got %q", message)
	}
	if strings.Contains(message, "secret upstream payload") {
		t.Fatalf("error leaked upstream response body: %q", message)
	}
}
