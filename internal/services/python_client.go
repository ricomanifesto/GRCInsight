package services

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
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

    client := &PythonServiceClient{
        lambdaClient:   lambdaClient,
        functionName:   functionName,
        isLambdaMode:   isLambdaMode,
        invokeAsync:    invokeAsync,
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

	return nil, fmt.Errorf("Lambda mode not available - PYTHON_LAMBDA_FUNCTION_NAME environment variable not set")
}

// RunWorkflowAsync triggers the Python Lambda asynchronously (no response expected)
func (c *PythonServiceClient) RunWorkflowAsync(req *models.WorkflowRequest, reportID string) error {
    if !c.isLambdaMode {
        return fmt.Errorf("Lambda mode not available - PYTHON_LAMBDA_FUNCTION_NAME environment variable not set")
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
	// For Lambda mode, we'll use the main workflow instead of separate analysis
	// This can be enhanced later to support specific analysis endpoints
	return nil, fmt.Errorf("AnalyzeArticles not yet implemented for Lambda mode - use RunWorkflow instead")
}

// HealthCheck checks if the Python service is healthy
func (c *PythonServiceClient) HealthCheck() error {
	if !c.isLambdaMode {
		return fmt.Errorf("Lambda mode not available - PYTHON_LAMBDA_FUNCTION_NAME environment variable not set")
	}

	// For Lambda functions, we can test connectivity by doing a simple invoke
	// with a health check payload
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Simple health check payload
	payload := map[string]interface{}{
		"health_check": true,
	}

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
