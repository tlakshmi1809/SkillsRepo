#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration defaults
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="mcp-rest-server"
AR_REPO="mcp-servers"

echo "=========================================================="
echo "☁️ FastMCP Server - Google Cloud Run Deployment Script"
echo "=========================================================="

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID is not set and gcloud has no active project configured."
    echo "Usage: GCP_PROJECT_ID=your-project-id GCP_REGION=us-central1 ./deploy_cloudrun.sh"
    exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:latest"

echo "Project ID : $PROJECT_ID"
echo "Region     : $REGION"
echo "Image URI  : $IMAGE_URI"
echo "----------------------------------------------------------"

# 1. Enable Required GCP APIs
echo "1️⃣ Enabling Google Cloud APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com --project="$PROJECT_ID"

# 2. Create Artifact Registry Repository if needed
echo "2️⃣ Checking Artifact Registry..."
if ! gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating Artifact Registry repository '$AR_REPO'..."
    gcloud artifacts repositories create "$AR_REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --description="Docker repository for MCP servers"
fi

# 3. Build & Push Image using Cloud Build
echo "3️⃣ Building & Pushing Container Image via Cloud Build..."
gcloud builds submit --tag "$IMAGE_URI" --project="$PROJECT_ID" .

# 4. Deploy to Cloud Run
echo "4️⃣ Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_URI" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --platform=managed \
    --allow-unauthenticated \
    --set-env-vars="API_BASE_URL=${API_BASE_URL:-https://httpbin.org},AUTH_SCHEME=${AUTH_SCHEME:-Bearer}"

URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')

echo "=========================================================="
echo "🎉 Cloud Run Deployment Successful!"
echo "Service Endpoint: $URL"
echo "=========================================================="
