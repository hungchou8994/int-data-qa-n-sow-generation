#!/bin/bash

# Cloud Run Deployment Script for Questionnaire Generator
# This script deploys the Streamlit app to Google Cloud Run

# Configuration
PROJECT_ID="int-data-qa-n-sow-generation"
REGION="asia-southeast1"
SERVICE_NAME="questionnaire-generator"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "============================================"
echo "Cloud Run Deployment Script"
echo "============================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "============================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ ERROR: gcloud CLI is not installed"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ gcloud CLI found"

# Set project
echo ""
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo ""
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Build and push Docker image
echo ""
echo "🐳 Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME}

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"

# Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=service-account-key:latest"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Deployment failed"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ Deployment completed successfully!"
echo "============================================"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')

echo ""
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""
echo "📝 Next steps:"
echo "1. Open the URL in your browser"
echo "2. Test the questionnaire generation"
echo "3. Monitor logs: gcloud run logs tail ${SERVICE_NAME} --region ${REGION}"
echo ""
