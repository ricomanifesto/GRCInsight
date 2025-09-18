#!/bin/bash

# AWS Lambda Deployment Script for GRCInsight
set -e

echo "Deploying GRCInsight to AWS Lambda..."

# Configuration
export DOCKER_BUILDKIT=0
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
GO_REPO_NAME=grcinsight-go
PYTHON_REPO_NAME=grcinsight-python
GO_FUNCTION_NAME=grcinsight-go-function
PYTHON_FUNCTION_NAME=grcinsight-python-function

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

print_status "AWS Account ID: $AWS_ACCOUNT_ID"
print_status "AWS Region: $AWS_REGION"

# Ensure OpenAI API key is present for Python Lambda
if [ -z "${OPENAI_API_KEY}" ]; then
    print_error "OPENAI_API_KEY is not set. Export OPENAI_API_KEY before deploying."
    exit 1
fi

# Step 1: Create ECR repositories if they don't exist
print_status "Creating ECR repositories..."

for repo in $GO_REPO_NAME $PYTHON_REPO_NAME; do
    if ! aws ecr describe-repositories --repository-names $repo --region $AWS_REGION > /dev/null 2>&1; then
        print_warning "Creating ECR repository: $repo"
        aws ecr create-repository \
            --repository-name $repo \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true
    else
        print_status "ECR repository $repo already exists"
    fi
done

# Step 2: Login to ECR
print_status "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Step 3: Build and push Go Lambda function
print_status "Building Go Lambda function (BuildKit disabled for Lambda manifest compatibility)..."
docker build -f Dockerfile.lambda -t $GO_REPO_NAME:latest .
docker tag $GO_REPO_NAME:latest $ECR_REGISTRY/$GO_REPO_NAME:latest

print_status "Pushing Go Lambda function to ECR..."
docker push $ECR_REGISTRY/$GO_REPO_NAME:latest

GO_IMAGE_URI=$ECR_REGISTRY/$GO_REPO_NAME:latest

# Step 4: Build and push Python Lambda function
print_status "Building Python Lambda function (BuildKit disabled for Lambda manifest compatibility)..."
cd agent
docker build -f Dockerfile.lambda -t $PYTHON_REPO_NAME:latest .
docker tag $PYTHON_REPO_NAME:latest $ECR_REGISTRY/$PYTHON_REPO_NAME:latest

print_status "Pushing Python Lambda function to ECR..."
docker push $ECR_REGISTRY/$PYTHON_REPO_NAME:latest

PYTHON_IMAGE_URI=$ECR_REGISTRY/$PYTHON_REPO_NAME:latest
cd ..

# Step 5: Create or update Lambda functions
print_status "Creating/updating Lambda functions..."

# Create execution role if it doesn't exist
ROLE_NAME=grcinsight-lambda-role
if ! aws iam get-role --role-name $ROLE_NAME > /dev/null 2>&1; then
    print_warning "Creating IAM role for Lambda..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }'

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Wait for role to be available
    sleep 10
else
    print_status "IAM role $ROLE_NAME already exists"
fi

ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}

# Create/update Go Lambda function
print_status "Deploying Go Lambda function..."
if aws lambda get-function --function-name $GO_FUNCTION_NAME --region $AWS_REGION > /dev/null 2>&1; then
    print_warning "Updating existing Go Lambda function..."
    aws lambda update-function-code \
        --function-name $GO_FUNCTION_NAME \
        --image-uri $GO_IMAGE_URI \
        --region $AWS_REGION
    # Ensure environment variables are configured
    aws lambda update-function-configuration \
        --function-name $GO_FUNCTION_NAME \
        --region $AWS_REGION \
        --environment Variables="{\n            GO_ENV=production,\n            GIN_MODE=release,\n            PYTHON_LAMBDA_FUNCTION_NAME=$PYTHON_FUNCTION_NAME,\n            PYTHON_INVOKE_ASYNC=true\n        }"
else
    print_warning "Creating new Go Lambda function..."
    aws lambda create-function \
        --function-name $GO_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$GO_IMAGE_URI \
        --role $ROLE_ARN \
        --timeout 900 \
        --memory-size 1024 \
        --region $AWS_REGION \
        --environment Variables="{\n            GO_ENV=production,\n            GIN_MODE=release,\n            PYTHON_LAMBDA_FUNCTION_NAME=$PYTHON_FUNCTION_NAME,\n            PYTHON_INVOKE_ASYNC=true\n        }"
fi

# Create/update Python Lambda function
print_status "Deploying Python Lambda function..."
if aws lambda get-function --function-name $PYTHON_FUNCTION_NAME --region $AWS_REGION > /dev/null 2>&1; then
    print_warning "Updating existing Python Lambda function..."
    aws lambda update-function-code \
        --function-name $PYTHON_FUNCTION_NAME \
        --image-uri $PYTHON_IMAGE_URI \
        --region $AWS_REGION
    # Ensure environment variables are configured
    aws lambda update-function-configuration \
        --function-name $PYTHON_FUNCTION_NAME \
        --region $AWS_REGION \
        --environment Variables="{\n            OPENAI_API_KEY=${OPENAI_API_KEY:-},\n            LOG_LEVEL=INFO,\n            DDB_TABLE_NAME=grcinsight-reports\n        }"
else
    print_warning "Creating new Python Lambda function..."
    aws lambda create-function \
        --function-name $PYTHON_FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$PYTHON_IMAGE_URI \
        --role $ROLE_ARN \
        --timeout 900 \
        --memory-size 2048 \
        --region $AWS_REGION \
        --environment Variables="{\n            OPENAI_API_KEY=${OPENAI_API_KEY:-},\n            LOG_LEVEL=INFO,\n            DDB_TABLE_NAME=grcinsight-reports\n        }"
fi

# Ensure IAM policy for DynamoDB and Lambda invoke is attached to the role
print_status "Ensuring IAM policies for DynamoDB and Lambda invoke..."
POLICY_NAME=grcinsight-lambda-permissions
POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='$POLICY_NAME'].Arn | [0]" --output text 2>/dev/null || echo "None")
if [ "$POLICY_ARN" = "None" ] || [ -z "$POLICY_ARN" ]; then
    print_warning "Creating customer managed policy: $POLICY_NAME"
    POLICY_ARN=$(aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file://deployments/lambda-permissions-policy.json \
        --query 'Policy.Arn' --output text)
else
    print_status "Policy $POLICY_NAME already exists: $POLICY_ARN"
fi

ATTACHED=$(aws iam list-attached-role-policies --role-name $ROLE_NAME --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN'] | length(@)" --output text)
if [ "$ATTACHED" = "0" ]; then
    print_warning "Attaching policy $POLICY_NAME to role $ROLE_NAME"
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn $POLICY_ARN
else
    print_status "Role $ROLE_NAME already has policy $POLICY_NAME attached"
fi

# Step 6: Summary
print_status "Lambda functions deployed successfully!"
echo
echo "Deployment Summary:"
echo "  Go Function: $GO_FUNCTION_NAME"
echo "  Python Function: $PYTHON_FUNCTION_NAME"
echo "  Region: $AWS_REGION"
echo
echo "To invoke functions:"
echo "  aws lambda invoke --function-name $GO_FUNCTION_NAME output.json"
echo "  aws lambda invoke --function-name $PYTHON_FUNCTION_NAME output.json"
echo
print_status "Deployment completed!"
