package services

import (
	"encoding/json"
	"io"
	"net/http"
	"strconv"
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

func TestAnalyzeArticlesPropagatesItsCallerDeadline(t *testing.T) {
	var propagatedDeadline int64
	timeout := 5 * time.Second
	startedAt := time.Now()
	client := &PythonServiceClient{
		httpClient: &http.Client{
			Timeout: timeout,
			Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
				value := req.Header.Get(callerDeadlineHeader)
				var err error
				propagatedDeadline, err = strconv.ParseInt(value, 10, 64)
				if err != nil {
					t.Fatalf("parse propagated deadline %q: %v", value, err)
				}
				return &http.Response{
					StatusCode: http.StatusOK,
					Body: io.NopCloser(strings.NewReader(
						`{"status":"success","results":[],"summary":{}}`,
					)),
					Header:  make(http.Header),
					Request: req,
				}, nil
			}),
		},
		baseURL: "http://python-service.test",
		logger:  logrus.New(),
	}

	if _, err := client.AnalyzeArticles(&models.AnalysisRequest{}); err != nil {
		t.Fatalf("analyze articles: %v", err)
	}

	minimum := startedAt.Add(timeout - time.Second).UnixMilli()
	maximum := time.Now().Add(timeout + time.Second).UnixMilli()
	if propagatedDeadline < minimum || propagatedDeadline > maximum {
		t.Fatalf("propagated deadline %d outside expected range [%d, %d]", propagatedDeadline, minimum, maximum)
	}
}

func TestWorkflowPayloadIncludesDeadlineOnlyForSynchronousCalls(t *testing.T) {
	req := &models.WorkflowRequest{FeedURL: "https://example.com/feed.xml"}
	deadline := time.UnixMilli(1_800_000)

	syncPayload, err := marshalWorkflowPayload(req, "", deadline)
	if err != nil {
		t.Fatalf("marshal synchronous payload: %v", err)
	}
	var syncEvent map[string]any
	if err := json.Unmarshal(syncPayload, &syncEvent); err != nil {
		t.Fatalf("decode synchronous payload: %v", err)
	}
	if got := int64(syncEvent[callerDeadlineField].(float64)); got != deadline.UnixMilli() {
		t.Fatalf("expected caller deadline %d, got %d", deadline.UnixMilli(), got)
	}

	asyncPayload, err := marshalWorkflowPayload(req, "report-1", time.Time{})
	if err != nil {
		t.Fatalf("marshal asynchronous payload: %v", err)
	}
	var asyncEvent map[string]any
	if err := json.Unmarshal(asyncPayload, &asyncEvent); err != nil {
		t.Fatalf("decode asynchronous payload: %v", err)
	}
	if _, ok := asyncEvent[callerDeadlineField]; ok {
		t.Fatal("asynchronous payload must not inherit the submission caller deadline")
	}
}

func TestHTTPWorkflowPropagatesItsCallerDeadline(t *testing.T) {
	var propagatedDeadline int64
	timeout := 5 * time.Second
	startedAt := time.Now()
	client := &PythonServiceClient{
		httpClient: &http.Client{
			Timeout: timeout,
			Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
				value := req.Header.Get(callerDeadlineHeader)
				var err error
				propagatedDeadline, err = strconv.ParseInt(value, 10, 64)
				if err != nil {
					t.Fatalf("parse propagated deadline %q: %v", value, err)
				}
				return &http.Response{
					StatusCode: http.StatusOK,
					Body:       io.NopCloser(strings.NewReader(`{"status":"completed"}`)),
					Header:     make(http.Header),
					Request:    req,
				}, nil
			}),
		},
		baseURL: "http://python-service.test",
		logger:  logrus.New(),
	}

	if _, err := client.RunWorkflow(&models.WorkflowRequest{FeedURL: "https://example.com/feed.xml"}); err != nil {
		t.Fatalf("run workflow: %v", err)
	}

	minimum := startedAt.Add(timeout - time.Second).UnixMilli()
	maximum := time.Now().Add(timeout + time.Second).UnixMilli()
	if propagatedDeadline < minimum || propagatedDeadline > maximum {
		t.Fatalf("propagated deadline %d outside expected range [%d, %d]", propagatedDeadline, minimum, maximum)
	}
}
