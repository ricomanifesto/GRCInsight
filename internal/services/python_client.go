package services

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
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

// PythonServiceClient handles communication with the Python agent service
type PythonServiceClient struct {
    lambdaClient   *lambda.Client
    functionName   string
    isLambdaMode   bool
    invokeAsync    bool
    httpClient     *http.Client
    baseURL        string
    logger         *logrus.Logger
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
        if env == "1" || env == "true" || env == "TRUE" {
            invokeAsync = true
        } else if env == "0" || env == "false" || env == "FALSE" {
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
                "function_name":            functionName,
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
        lambdaClient:   lambdaClient,
        functionName:   functionName,
        isLambdaMode:   isLambdaMode,
        invokeAsync:    invokeAsync,
        httpClient:     httpClient,
        baseURL:        baseURL,
        logger:         logger,
    }

    logger.WithFields(logrus.Fields{
        "lambda_mode":  client.isLambdaMode,
        "invoke_async": client.invokeAsync,
        "function_name": client.functionName,
    }).Info("PythonServiceClient initialized")

    return client
}

// RunWorkflow executes the complete GRC analysis workflow
func (c *PythonServiceClient) RunWorkflow(req *models.WorkflowRequest) (*models.WorkflowResponse, error) {
    c.logger.WithFields(logrus.Fields{
        "lambda_mode":  c.isLambdaMode,
        "function_name": c.functionName,
    }).Info("Starting Python workflow execution")

    if c.isLambdaMode {
        return c.invokeLambdaWorkflow(req)
    }

    // HTTP mode
    return c.invokeHTTPWorkflow(req)
}

// RunWorkflowAsync triggers the Python Lambda asynchronously (no response expected)
func (c *PythonServiceClient) RunWorkflowAsync(req *models.WorkflowRequest, reportID string) error {
    if !c.isLambdaMode {
        // For HTTP mode, we don't support async fire-and-forget yet
        return fmt.Errorf("async invocation not supported in HTTP mode")
    }
    if c.lambdaClient == nil {
        return fmt.Errorf("Lambda client not initialized")
    }

    c.logger.WithFields(logrus.Fields{
        "function_name": c.functionName,
        "report_id":     reportID,
    }).Info("Invoking Python Lambda function asynchronously")

    payload := map[string]interface{}{
        "report_id": reportID,
        "feed_url":  req.FeedURL,
        "config":    req.Config,
    }

    payloadBytes, err := json.Marshal(payload)
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

	// Create the payload for Lambda invocation
	payload := map[string]interface{}{
		"feed_url": req.FeedURL,
		"config":   req.Config,
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal Lambda payload: %w", err)
	}

	c.logger.WithField("payload_size", len(payloadBytes)).Debug("Invoking Lambda function")

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

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
		return nil, fmt.Errorf("Python Lambda function error: %s", string(result.Payload))
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
		return nil, fmt.Errorf("Python Lambda returned error status: %d", lambdaResponse.StatusCode)
	}

	if lambdaResponse.Body == nil {
		return nil, fmt.Errorf("Python Lambda returned empty response body")
	}

	c.logger.WithField("status", lambdaResponse.Body.Status).Info("Python workflow completed via Lambda")
	return lambdaResponse.Body, nil
}

// AnalyzeArticles sends articles to Python service for GRC analysis
func (c *PythonServiceClient) AnalyzeArticles(req *models.AnalysisRequest) (*models.AnalysisResponse, error) {
    if c.isLambdaMode {
        // Not implemented for Lambda path
        return nil, fmt.Errorf("AnalyzeArticles not implemented for Lambda mode - use RunWorkflow instead")
    }

    // HTTP mode: POST to Python service
    url := c.baseURL + "/api/v1/analyze"
    bodyBytes, err := json.Marshal(req)
    if err != nil {
        return nil, fmt.Errorf("failed to marshal analysis request: %w", err)
    }

    httpReq, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(bodyBytes))
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    httpReq.Header.Set("Content-Type", "application/json")

    resp, err := c.httpClient.Do(httpReq)
    if err != nil {
        return nil, fmt.Errorf("python service request failed: %w", err)
    }
    defer resp.Body.Close()
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        b, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("python service returned %d: %s", resp.StatusCode, string(b))
    }

    var ar models.AnalysisResponse
    if err := json.NewDecoder(resp.Body).Decode(&ar); err != nil {
        return nil, fmt.Errorf("failed to decode analysis response: %w", err)
    }
    return &ar, nil
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
            return fmt.Errorf("Python Lambda health check failed: %s", string(result.Payload))
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
    defer resp.Body.Close()
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        b, _ := io.ReadAll(resp.Body)
        return fmt.Errorf("python service health returned %d: %s", resp.StatusCode, string(b))
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

    httpReq, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(bodyBytes))
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    httpReq.Header.Set("Content-Type", "application/json")

    resp, err := c.httpClient.Do(httpReq)
    if err != nil {
        return nil, fmt.Errorf("python service request failed: %w", err)
    }
    defer resp.Body.Close()
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        b, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("python service returned %d: %s", resp.StatusCode, string(b))
    }

    var wr models.WorkflowResponse
    if err := json.NewDecoder(resp.Body).Decode(&wr); err != nil {
        return nil, fmt.Errorf("failed to decode workflow response: %w", err)
    }
    return &wr, nil
}
