package services

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"grcinsight/internal/config"
	"grcinsight/internal/models"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/lambda"
	"github.com/aws/aws-sdk-go-v2/service/lambda/types"
	"github.com/sirupsen/logrus"
)

const (
	callerDeadlineField    = "caller_deadline_unix_ms"
	callerDeadlineHeader   = "X-GRC-Caller-Deadline-Unix-Ms"
	defaultWorkflowTimeout = 5 * time.Minute
)

// PythonServiceClient handles communication with the Python agent service
type PythonServiceClient struct {
	lambdaClient *lambda.Client
	functionName string
	isLambdaMode bool
	invokeAsync  bool
	httpClient   *http.Client
	baseURL      string
	logger       *logrus.Logger
}

// NewPythonServiceClient creates a new Python service client
func NewPythonServiceClient(cfg config.PythonServiceConfig, logger *logrus.Logger) *PythonServiceClient {
	// Determine function name from config or environment
	functionName := cfg.LambdaFunctionName
	if functionName == "" {
		functionName = os.Getenv("PYTHON_LAMBDA_FUNCTION_NAME")
	}
	isLambdaMode := functionName != ""
	// Async mode via config or env override
	invokeAsync := cfg.InvokeAsync
	if env := os.Getenv("PYTHON_INVOKE_ASYNC"); env != "" {
		switch env {
		case "1", "true", "TRUE":
			invokeAsync = true
		case "0", "false", "FALSE":
			invokeAsync = false
		}
	}

	var lambdaClient *lambda.Client
	if isLambdaMode {
		// Initialize AWS Lambda client
		awsCfg, err := awsconfig.LoadDefaultConfig(context.Background())
		if err != nil {
			logger.WithError(err).Error("Failed to load AWS config, falling back to HTTP client")
			isLambdaMode = false
		} else {
			lambdaClient = lambda.NewFromConfig(awsCfg)
			logger.WithFields(logrus.Fields{
				"function_name":             functionName,
				"aws_lambda_runtime_detect": os.Getenv("AWS_LAMBDA_FUNCTION_NAME") != "",
			}).Info("Lambda client initialized for Python service")
		}
	}

	// Build HTTP client regardless (used when not in Lambda mode)
	httpClient := &http.Client{Timeout: cfg.Timeout}
	baseURL := cfg.URL
	if baseURL == "" {
		baseURL = "http://localhost:8081"
	}
	baseURL = strings.TrimRight(baseURL, "/")

	client := &PythonServiceClient{
		lambdaClient: lambdaClient,
		functionName: functionName,
		isLambdaMode: isLambdaMode,
		invokeAsync:  invokeAsync,
		httpClient:   httpClient,
		baseURL:      baseURL,
		logger:       logger,
	}

	logger.WithFields(logrus.Fields{
		"lambda_mode":   client.isLambdaMode,
		"invoke_async":  client.invokeAsync,
		"function_name": client.functionName,
	}).Info("PythonServiceClient initialized")

	return client
}

// RunWorkflow executes the complete GRC analysis workflow
func (c *PythonServiceClient) RunWorkflow(req *models.WorkflowRequest) (*models.WorkflowResponse, error) {
	c.logger.WithFields(logrus.Fields{
		"lambda_mode":   c.isLambdaMode,
		"function_name": c.functionName,
	}).Info("Starting Python workflow execution")

	if c.isLambdaMode {
		return c.invokeLambdaWorkflow(req)
	}

	// HTTP mode
	return c.invokeHTTPWorkflow(req)
}

func (c *PythonServiceClient) workflowTimeout() time.Duration {
	if c.httpClient != nil && c.httpClient.Timeout > 0 {
		return c.httpClient.Timeout
	}
	return defaultWorkflowTimeout
}

func (c *PythonServiceClient) newCallerBoundRequest(
	method string,
	url string,
	body []byte,
) (*http.Request, context.CancelFunc, error) {
	ctx, cancel := context.WithTimeout(context.Background(), c.workflowTimeout())
	callerDeadline, _ := ctx.Deadline()
	httpReq, err := http.NewRequestWithContext(ctx, method, url, bytes.NewReader(body))
	if err != nil {
		cancel()
		return nil, nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set(callerDeadlineHeader, strconv.FormatInt(callerDeadline.UnixMilli(), 10))
	return httpReq, cancel, nil
}

// WorkflowJob identifies one admitted generation job for an existing report row.
type WorkflowJob struct {
	ReportID string
	JobID    string
}

// ErrCompletionRefused means the report writer refused this completion because the
// report already has a final outcome or belongs to another job.
var ErrCompletionRefused = errors.New("report completion refused")

func marshalWorkflowPayload(
	req *models.WorkflowRequest,
	job WorkflowJob,
	callerDeadline time.Time,
) ([]byte, error) {
	payload := map[string]interface{}{
		"feed_url": req.FeedURL,
		"config":   req.Config,
	}
	if job.ReportID != "" {
		payload["report_id"] = job.ReportID
	}
	if job.JobID != "" {
		payload["job_id"] = job.JobID
	}
	if !callerDeadline.IsZero() {
		payload[callerDeadlineField] = callerDeadline.UnixMilli()
	}
	return json.Marshal(payload)
}

// RunWorkflowAsync triggers the Python Lambda asynchronously (no response expected)
func (c *PythonServiceClient) RunWorkflowAsync(req *models.WorkflowRequest, job WorkflowJob) error {
	if !c.isLambdaMode {
		// For HTTP mode, we don't support async fire-and-forget yet
		return fmt.Errorf("async invocation not supported in HTTP mode")
	}
	if c.lambdaClient == nil {
		return fmt.Errorf("lambda client not initialized")
	}

	c.logger.WithFields(logrus.Fields{
		"function_name": c.functionName,
		"report_id":     job.ReportID,
	}).Info("Invoking Python Lambda function asynchronously")

	payloadBytes, err := marshalWorkflowPayload(req, job, time.Time{})
	if err != nil {
		return fmt.Errorf("failed to marshal Lambda payload: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	input := &lambda.InvokeInput{
		FunctionName:   aws.String(c.functionName),
		Payload:        payloadBytes,
		InvocationType: types.InvocationTypeEvent,
	}

	if _, err := c.lambdaClient.Invoke(ctx, input); err != nil {
		return fmt.Errorf("failed to invoke Python Lambda asynchronously: %w", err)
	}

	c.logger.Info("Asynchronous Lambda invocation submitted")
	return nil
}

// IsAsync indicates whether client is configured to use async invocation
func (c *PythonServiceClient) IsAsync() bool { return c.invokeAsync }

// invokeLambdaWorkflow invokes the Python Lambda function directly
func (c *PythonServiceClient) invokeLambdaWorkflow(req *models.WorkflowRequest) (*models.WorkflowResponse, error) {
	c.logger.WithField("function_name", c.functionName).Info("Invoking Python Lambda function")

	ctx, cancel := context.WithTimeout(context.Background(), c.workflowTimeout())
	defer cancel()
	callerDeadline, _ := ctx.Deadline()

	payloadBytes, err := marshalWorkflowPayload(req, WorkflowJob{}, callerDeadline)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal Lambda payload: %w", err)
	}

	c.logger.WithField("payload_size", len(payloadBytes)).Debug("Invoking Lambda function")

	// Invoke the Lambda function
	input := &lambda.InvokeInput{
		FunctionName: aws.String(c.functionName),
		Payload:      payloadBytes,
	}

	result, err := c.lambdaClient.Invoke(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to invoke Python Lambda function: %w", err)
	}

	// Check for function errors
	if result.FunctionError != nil {
		return nil, fmt.Errorf("python Lambda function error: %s", string(result.Payload))
	}

	c.logger.WithFields(logrus.Fields{
		"status_code":    result.StatusCode,
		"payload_size":   len(result.Payload),
		"execution_time": result.ExecutedVersion,
	}).Info("Lambda function executed successfully")

	// Parse the Lambda response
	var lambdaResponse struct {
		StatusCode int                      `json:"statusCode"`
		Body       *models.WorkflowResponse `json:"body"`
	}

	if err := json.Unmarshal(result.Payload, &lambdaResponse); err != nil {
		return nil, fmt.Errorf("failed to decode Lambda response: %w", err)
	}

	if lambdaResponse.StatusCode != 200 {
		return nil, fmt.Errorf("python Lambda returned error status: %d", lambdaResponse.StatusCode)
	}

	if lambdaResponse.Body == nil {
		return nil, fmt.Errorf("python Lambda returned empty response body")
	}

	c.logger.WithField("status", lambdaResponse.Body.Status).Info("Python workflow completed via Lambda")
	return lambdaResponse.Body, nil
}

// HealthCheck checks if the Python service is healthy
func (c *PythonServiceClient) HealthCheck() error {
	if c.isLambdaMode {
		// For Lambda functions, test connectivity by a simple invoke
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		payload := map[string]interface{}{"health_check": true}
		payloadBytes, err := json.Marshal(payload)
		if err != nil {
			return fmt.Errorf("failed to marshal health check payload: %w", err)
		}
		input := &lambda.InvokeInput{
			FunctionName: aws.String(c.functionName),
			Payload:      payloadBytes,
		}
		result, err := c.lambdaClient.Invoke(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to invoke Python Lambda for health check: %w", err)
		}
		if result.FunctionError != nil {
			return fmt.Errorf("python Lambda health check failed: %s", string(result.Payload))
		}
		c.logger.Debug("Python Lambda health check passed")
		return nil
	}

	// HTTP mode: GET /health
	url := c.baseURL + "/api/v1/health"
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return fmt.Errorf("failed to create health request: %w", err)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("python service health request failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("python service health returned %d", resp.StatusCode)
	}

	// Optionally parse to verify status
	var hs models.HealthStatus
	if err := json.NewDecoder(resp.Body).Decode(&hs); err == nil {
		if strings.ToLower(hs.Status) != "healthy" {
			return fmt.Errorf("python service unhealthy: %s", hs.Status)
		}
	}
	return nil
}

// invokeHTTPWorkflow calls the Python FastAPI service synchronously
func (c *PythonServiceClient) invokeHTTPWorkflow(req *models.WorkflowRequest) (*models.WorkflowResponse, error) {
	url := c.baseURL + "/api/v1/workflow/run"
	bodyBytes, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal workflow request: %w", err)
	}

	httpReq, cancel, err := c.newCallerBoundRequest(http.MethodPost, url, bodyBytes)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	defer cancel()

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("python service request failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("python service returned %d", resp.StatusCode)
	}

	var wr models.WorkflowResponse
	if err := json.NewDecoder(resp.Body).Decode(&wr); err != nil {
		return nil, fmt.Errorf("failed to decode workflow response: %w", err)
	}
	return &wr, nil
}

// RunWorkflowForReport runs the workflow synchronously for an admitted report and
// lets the Python report writer commit it, so synchronous and asynchronous
// generation share one completion contract. Go never writes the outcome itself.
func (c *PythonServiceClient) RunWorkflowForReport(req *models.WorkflowRequest, job WorkflowJob) error {
	if job.ReportID == "" {
		return fmt.Errorf("report id is required")
	}
	if c.isLambdaMode {
		ctx, cancel := context.WithTimeout(context.Background(), c.workflowTimeout())
		defer cancel()
		callerDeadline, _ := ctx.Deadline()
		payload, err := marshalWorkflowPayload(req, job, callerDeadline)
		if err != nil {
			return fmt.Errorf("failed to marshal Lambda payload: %w", err)
		}
		result, err := c.lambdaClient.Invoke(ctx, &lambda.InvokeInput{
			FunctionName: aws.String(c.functionName),
			Payload:      payload,
		})
		if err != nil {
			return fmt.Errorf("failed to invoke Python Lambda function: %w", err)
		}
		if result.FunctionError != nil {
			return fmt.Errorf("python Lambda function error")
		}
		var envelope struct {
			StatusCode int             `json:"statusCode"`
			Body       json.RawMessage `json:"body"`
		}
		if err := json.Unmarshal(result.Payload, &envelope); err != nil {
			return fmt.Errorf("failed to decode Lambda response: %w", err)
		}
		return decodeReportCompletion(envelope.StatusCode, envelope.Body)
	}

	body, err := json.Marshal(map[string]any{
		"feed_url": req.FeedURL,
		"config":   req.Config,
		"job_id":   job.JobID,
	})
	if err != nil {
		return fmt.Errorf("failed to marshal workflow request: %w", err)
	}
	endpoint := c.baseURL + "/api/v1/workflow/reports/" + url.PathEscape(job.ReportID) + "/run"
	httpReq, cancel, err := c.newCallerBoundRequest(http.MethodPost, endpoint, body)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	defer cancel()
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("python service request failed: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 64<<10))
	if err != nil {
		return fmt.Errorf("failed to read workflow response: %w", err)
	}
	return decodeReportCompletion(resp.StatusCode, raw)
}

// decodeReportCompletion maps the report writer's decision to an error, without
// echoing response bodies into logs or errors.
func decodeReportCompletion(status int, body []byte) error {
	var decision struct {
		Decision string `json:"decision"`
	}
	_ = json.Unmarshal(body, &decision)
	switch {
	case status == http.StatusOK && (decision.Decision == "committed" || decision.Decision == "reused"):
		return nil
	case status == http.StatusConflict:
		return fmt.Errorf("%w: %s", ErrCompletionRefused, decision.Decision)
	case decision.Decision != "":
		return fmt.Errorf("report writer returned %d: %s", status, decision.Decision)
	default:
		return fmt.Errorf("report writer returned %d", status)
	}
}
