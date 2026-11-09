package services

import (
	"encoding/json"
	"errors"
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

func TestHTTPWorkflowRedactsErrorResponseBody(t *testing.T) {
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

	_, err := client.RunWorkflow(&models.WorkflowRequest{FeedURL: "https://example.com/feed.xml"})
	if err == nil {
		t.Fatal("expected RunWorkflow to return an error")
	}

	message := err.Error()
	if !strings.Contains(message, "python service returned 500") {
		t.Fatalf("expected status code in error, got %q", message)
	}
	if strings.Contains(message, "secret upstream payload") {
		t.Fatalf("error leaked upstream response body: %q", message)
	}
}

func TestWorkflowPayloadIncludesDeadlineOnlyForSynchronousCalls(t *testing.T) {
	req := &models.WorkflowRequest{FeedURL: "https://example.com/feed.xml"}
	deadline := time.UnixMilli(1_800_000)

	syncPayload, err := marshalWorkflowPayload(req, WorkflowJob{}, deadline)
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

	asyncPayload, err := marshalWorkflowPayload(req, WorkflowJob{ReportID: "report-1", JobID: "job-1"}, time.Time{})
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
	if asyncEvent["report_id"] != "report-1" || asyncEvent["job_id"] != "job-1" {
		t.Fatalf("payload does not bind the admitted job: %v", asyncEvent)
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

func reportWriterClient(status int, body string, seen *http.Request, sent *map[string]any) *PythonServiceClient {
	return &PythonServiceClient{
		httpClient: &http.Client{
			Timeout: time.Second,
			Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
				*seen = *req
				raw, _ := io.ReadAll(req.Body)
				_ = json.Unmarshal(raw, sent)
				return &http.Response{
					StatusCode: status,
					Body:       io.NopCloser(strings.NewReader(body)),
					Header:     make(http.Header),
					Request:    req,
				}, nil
			}),
		},
		baseURL: "http://python-service.test",
		logger:  logrus.New(),
	}
}

func TestRunWorkflowForReportPostsTheAdmittedJob(t *testing.T) {
	var seen http.Request
	var sent map[string]any
	client := reportWriterClient(http.StatusOK, `{"decision":"committed"}`, &seen, &sent)
	client.internalToken = "synthetic-internal-token"
	job := WorkflowJob{ReportID: "report 1/x", JobID: "job-1"}
	if err := client.RunWorkflowForReport(&models.WorkflowRequest{FeedURL: "https://example.com/feed.xml"}, job); err != nil {
		t.Fatal(err)
	}
	if seen.URL.EscapedPath() != "/api/v1/workflow/reports/report%201%2Fx/run" {
		t.Fatalf("unexpected path %q", seen.URL.EscapedPath())
	}
	if sent["job_id"] != "job-1" || sent["feed_url"] != "https://example.com/feed.xml" {
		t.Fatalf("job not sent: %v", sent)
	}
	if seen.Header.Get(callerDeadlineHeader) == "" {
		t.Fatal("synchronous report run must carry the caller deadline")
	}
	if seen.Header.Get(internalTokenHeader) != "synthetic-internal-token" {
		t.Fatal("synchronous report run must authenticate to the report writer")
	}
}

func TestReportCompletionDecisions(t *testing.T) {
	cases := []struct {
		status  int
		body    string
		ok      bool
		refused bool
	}{
		{http.StatusOK, `{"decision":"committed"}`, true, false},
		{http.StatusOK, `{"decision":"reused"}`, true, false},
		{http.StatusConflict, `{"decision":"foreign_completion_refused"}`, false, true},
		{http.StatusInternalServerError, `{"decision":"evidence_failure_recorded"}`, false, false},
		{http.StatusOK, `{"decision":"something_else"}`, false, false},
		{http.StatusBadGateway, `secret upstream payload`, false, false},
	}
	for _, c := range cases {
		err := decodeReportCompletion(c.status, []byte(c.body))
		if (err == nil) != c.ok {
			t.Fatalf("%d %s: unexpected result %v", c.status, c.body, err)
		}
		if c.refused != errors.Is(err, ErrCompletionRefused) {
			t.Fatalf("%d %s: refusal classification wrong: %v", c.status, c.body, err)
		}
		if err != nil && strings.Contains(err.Error(), "secret") {
			t.Fatalf("error leaked the response body: %v", err)
		}
	}
}
