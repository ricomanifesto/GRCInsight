#!/bin/bash

# AWS Lambda Deployment Script for GRCInsight
set +x
set -eo pipefail
# Protect every direct/helper AWS descendant, including full configuration
# responses observed internally by existence checks and waiters.
export AWS_CLI_HISTORY_FILE=/dev

echo "Deploying GRCInsight to AWS Lambda..."

# Configuration
export DOCKER_BUILDKIT=0
AWS_REGION=${AWS_REGION:-us-east-1}
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

# Reuse the existing read-only STS check through the same filtered AWS CLI auth
# context as later environment writes, before any ECR/image/Lambda mutation.
AWS_ACCOUNT_ID=$(python3 -I -B scripts/update_lambda_environment.py \
    --function-kind python --preflight-only --manual-cli-auth --region "$AWS_REGION")
ECR_REGISTRY=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

print_status "AWS Account ID: $AWS_ACCOUNT_ID"
print_status "AWS Region: $AWS_REGION"

# Ensure model settings are present for Python Lambda
if [ -z "${LLM_MODEL}" ]; then
    print_error "LLM_MODEL is not set. Export LLM_MODEL before deploying."
    exit 1
fi

if [ -z "${OPENROUTER_API_KEY}" ]; then
    print_error "OPENROUTER_API_KEY is not set. Export OPENROUTER_API_KEY before deploying."
    exit 1
fi

case "$LLM_MODEL" in
    openrouter/*) ;;
    *)
        print_error "LLM_MODEL must use openrouter/provider-model format for direct Lambda model-backed analysis."
        exit 1
        ;;
esac

# Explicit operator bootstrap: verify runtime permissions before publishing images.
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
    print_status "Verifying existing runtime policy: $POLICY_NAME"
    POLICY_VERSION=$(aws iam get-policy --policy-arn "$POLICY_ARN" \
        --query 'Policy.DefaultVersionId' --output text)
    if ! aws iam get-policy-version --policy-arn "$POLICY_ARN" --version-id "$POLICY_VERSION" \
        --query 'PolicyVersion.Document' --output json | \
        jq -e --slurpfile expected deployments/lambda-permissions-policy.json '. == $expected[0]' > /dev/null; then
        print_error "Existing runtime policy requires owner reconciliation; no images or functions were updated."
        exit 1
    fi
fi

ATTACHED=$(aws iam list-attached-role-policies --role-name $ROLE_NAME --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN'] | length(@)" --output text)
if [ "$ATTACHED" = "0" ]; then
    print_warning "Attaching policy $POLICY_NAME to role $ROLE_NAME"
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn $POLICY_ARN
else
    print_status "Role $ROLE_NAME already has policy $POLICY_NAME attached"
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

print_status "Ensuring Lambda ECR retrieval policies are present..."
apply_ecr_policy() {
    local repo="$1" function_name="$2"
    local policy_file policy_error existing_policy
    policy_error=$(mktemp)
    if existing_policy=$(aws ecr get-repository-policy --repository-name "$repo" \
        --region "$AWS_REGION" --output json 2>"$policy_error"); then
        rm -f "$policy_error"
        # Preserve all existing statements and denies; never replace another
        # owner's policy. Broad or uncertain policies need explicit reconciliation.
        if ! printf '%s' "$existing_policy" | python3 -I -B scripts/check_ecr_retrieval_policy.py \
            --account-id "$AWS_ACCOUNT_ID" --region "$AWS_REGION" --function-name "$function_name"; then
            print_error "Existing ECR policy requires owner reconciliation; it was not changed."
            return 1
        fi
        return 0
    fi
    if ! grep -q 'RepositoryPolicyNotFoundException' "$policy_error"; then
        rm -f "$policy_error"
        print_error "Could not inspect ECR policy; no policy was changed."
        return 1
    fi
    rm -f "$policy_error"
    policy_file=$(mktemp)
    # This explicit operator bootstrap is separate from routine release IAM.
    # Bind service retrieval to this account and the matching function, including
    # inactive-function re-optimization; normal CI only verifies this grant.
    cat >"$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaECRImageRetrievalPolicy",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Condition": {
        "StringEquals": {"aws:SourceAccount": "$AWS_ACCOUNT_ID"},
        "ArnLike": {"aws:SourceArn": "arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:$function_name"}
      }
    }
  ]
}
EOF
    aws ecr set-repository-policy \
        --repository-name "$repo" \
        --region "$AWS_REGION" \
        --policy-text "file://$policy_file" > /dev/null
    rm -f "$policy_file"
    print_status "Applied Lambda ECR retrieval policy to $repo"
}

apply_ecr_policy "$GO_REPO_NAME" "$GO_FUNCTION_NAME"
apply_ecr_policy "$PYTHON_REPO_NAME" "$PYTHON_FUNCTION_NAME"

# Step 2: Login to ECR
print_status "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Step 3: Build and push Go Lambda function
print_status "Building Go Lambda function (BuildKit disabled for Lambda manifest compatibility)..."
docker build --platform linux/amd64 -f Dockerfile.lambda -t $GO_REPO_NAME:latest .
docker tag $GO_REPO_NAME:latest $ECR_REGISTRY/$GO_REPO_NAME:latest

print_status "Pushing Go Lambda function to ECR..."
docker push $ECR_REGISTRY/$GO_REPO_NAME:latest

GO_IMAGE_URI=$ECR_REGISTRY/$GO_REPO_NAME:latest

# Step 4: Build and push Python Lambda function
print_status "Building Python Lambda function (BuildKit disabled for Lambda manifest compatibility)..."
cd agent
docker build --platform linux/amd64 -f Dockerfile.lambda -t $PYTHON_REPO_NAME:latest .
docker tag $PYTHON_REPO_NAME:latest $ECR_REGISTRY/$PYTHON_REPO_NAME:latest

print_status "Pushing Python Lambda function to ECR..."
docker push $ECR_REGISTRY/$PYTHON_REPO_NAME:latest

PYTHON_IMAGE_URI=$ECR_REGISTRY/$PYTHON_REPO_NAME:latest
cd ..

# Step 5: Create or update Lambda functions
print_status "Creating/updating Lambda functions..."

ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}

# Create/update Go Lambda function
print_status "Deploying Go Lambda function..."
if aws lambda get-function --function-name $GO_FUNCTION_NAME --region $AWS_REGION > /dev/null 2>&1; then
    print_warning "Updating existing Go Lambda function..."
    aws lambda update-function-code \
        --function-name $GO_FUNCTION_NAME \
        --image-uri $GO_IMAGE_URI \
        --region $AWS_REGION \
        --query 'FunctionName' \
        --output text
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
        --query 'FunctionName' \
        --output text
fi

# Wait for code/create completion before the revision-checked environment merge.
aws lambda wait function-active-v2 --function-name "$GO_FUNCTION_NAME" --region "$AWS_REGION"
aws lambda wait function-updated-v2 --function-name "$GO_FUNCTION_NAME" --region "$AWS_REGION"
python3 -I -B scripts/update_lambda_environment.py \
    --function-kind go --account-id "$AWS_ACCOUNT_ID" --region "$AWS_REGION" --manual-cli-auth

# Create/update Python Lambda function
print_status "Deploying Python Lambda function..."
if aws lambda get-function --function-name $PYTHON_FUNCTION_NAME --region $AWS_REGION > /dev/null 2>&1; then
    print_warning "Updating existing Python Lambda function..."
    aws lambda update-function-code \
        --function-name $PYTHON_FUNCTION_NAME \
        --image-uri $PYTHON_IMAGE_URI \
        --region $AWS_REGION \
        --query 'FunctionName' \
        --output text
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
        --query 'FunctionName' \
        --output text
fi

aws lambda wait function-active-v2 --function-name "$PYTHON_FUNCTION_NAME" --region "$AWS_REGION"
aws lambda wait function-updated-v2 --function-name "$PYTHON_FUNCTION_NAME" --region "$AWS_REGION"
python3 -I -B scripts/update_lambda_environment.py \
    --function-kind python --account-id "$AWS_ACCOUNT_ID" --region "$AWS_REGION" --manual-cli-auth

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
