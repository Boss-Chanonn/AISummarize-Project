#!/usr/bin/env bash
set -euo pipefail

# ── Learnova Cloud Deploy Script ─────────────────────────────────────────────
# Usage:
#   ./deploy.sh                          # build + push to ECR + update Lambda
#   ./deploy.sh ecs                      # build + push to ECR + update ECS
#   BRIDGE_URL=http://54.206.73.1:8000 ./deploy.sh  # override bridge URL
#
# Prerequisites:
#   - AWS CLI installed & configured (aws configure)
#   - Docker running
#   - Edit the CONFIG section below with your actual AWS/ECR/ECS values
# ────────────────────────────────────────────────────────────────────────────

# ── CONFIG — fill these in ────────────────────────────────────────────────────
AWS_REGION="ap-southeast-2"         # your AWS region
ECR_REPO="learnova-app"             # ECR repository name
ECR_ACCOUNT="123456789012"          # your AWS account ID

LAMBDA_FUNCTION="learnova-api"      # Lambda function name (for Lambda deploy)
ECS_CLUSTER="learnova-cluster"      # ECS cluster name (for ECS deploy)
ECS_SERVICE="learnova-service"      # ECS service name (for ECS deploy)
ECS_CONTAINER="app"                # container name in task definition

# ── Build tag ─────────────────────────────────────────────────────────────────
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${GIT_HASH}-${TIMESTAMP}"
ECR_URI="${ECR_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# ── Step 1: Build Docker image ───────────────────────────────────────────────
echo "🔨 Building Docker image..."
docker build -t "${ECR_REPO}:${IMAGE_TAG}" -t "${ECR_REPO}:latest" .

# ── Step 2: Authenticate to ECR ──────────────────────────────────────────────
echo "🔐 Authenticating to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_URI}"

# ── Step 3: Tag & push ───────────────────────────────────────────────────────
echo "🏷️  Tagging image..."
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}/${ECR_REPO}:${IMAGE_TAG}"
docker tag "${ECR_REPO}:latest"       "${ECR_URI}/${ECR_REPO}:latest"

echo "📤 Pushing to ECR..."
docker push "${ECR_URI}/${ECR_REPO}:${IMAGE_TAG}"
docker push "${ECR_URI}/${ECR_REPO}:latest"

# ── Step 4: Deploy ────────────────────────────────────────────────────────────
DEPLOY_TARGET="${1:-lambda}"

if [ "$DEPLOY_TARGET" = "ecs" ]; then
  echo "🚀 Deploying to ECS — updating service ${ECS_SERVICE}..."
  aws ecs update-service \
    --cluster "${ECS_CLUSTER}" \
    --service "${ECS_SERVICE}" \
    --force-new-deployment \
    --region "${AWS_REGION}" \
    --output json \
    | jq '.service.serviceArn, .service.deployments[0].rolloutState'
  echo "✅ ECS deploy triggered. Image: ${ECR_URI}/${ECR_REPO}:${IMAGE_TAG}"
else
  echo "🚀 Deploying to Lambda — updating function ${LAMBDA_FUNCTION}..."
  aws lambda update-function-code \
    --function-name "${LAMBDA_FUNCTION}" \
    --image-uri "${ECR_URI}/${ECR_REPO}:latest" \
    --region "${AWS_REGION}" \
    --output json \
    | jq '{FunctionArn, LastUpdateStatus, State}'
  echo "✅ Lambda deploy triggered. Image: ${ECR_URI}/${ECR_REPO}:latest"
fi

echo ""
echo "── Done ─────────────────────────────────────────────────────────────"
echo "Image: ${ECR_URI}/${ECR_REPO}:${IMAGE_TAG}"
echo "Time:  $(date)"
