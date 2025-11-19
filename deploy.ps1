# Cloud Run Deployment Script for Questionnaire Generator (PowerShell)
# This script deploys the Streamlit app to Google Cloud Run

# Configuration
$PROJECT_ID = "int-data-qa-n-sow-generation"
$REGION = "asia-southeast1"
$SERVICE_NAME = "questionnaire-generator"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Cloud Run Deployment Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ID"
Write-Host "Region: $REGION"
Write-Host "Service: $SERVICE_NAME"
Write-Host "============================================" -ForegroundColor Cyan

# Check if gcloud is installed
if (!(Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "❌ ERROR: gcloud CLI is not installed" -ForegroundColor Red
    Write-Host "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
}

Write-Host "✅ gcloud CLI found" -ForegroundColor Green

# Set project
Write-Host ""
Write-Host "📋 Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

# Enable required APIs
Write-Host ""
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Build and push Docker image
Write-Host ""
Write-Host "🐳 Building Docker image..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker image built successfully" -ForegroundColor Green

# Get GOOGLE_API_KEY from environment
$GOOGLE_API_KEY = $env:GOOGLE_API_KEY
if (-not $GOOGLE_API_KEY) {
    Write-Host "⚠️ WARNING: GOOGLE_API_KEY not found in environment" -ForegroundColor Yellow
    Write-Host "The app may not work without it. Set it in Secret Manager or provide it now."
}

# Deploy to Cloud Run
Write-Host ""
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Yellow

if ($GOOGLE_API_KEY) {
    gcloud run deploy $SERVICE_NAME `
      --image $IMAGE_NAME `
      --platform managed `
      --region $REGION `
      --allow-unauthenticated `
      --memory 2Gi `
      --cpu 2 `
      --timeout 300 `
      --max-instances 10 `
      --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY" `
      --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=service-account-key:latest"
} else {
    gcloud run deploy $SERVICE_NAME `
      --image $IMAGE_NAME `
      --platform managed `
      --region $REGION `
      --allow-unauthenticated `
      --memory 2Gi `
      --cpu 2 `
      --timeout 300 `
      --max-instances 10 `
      --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=service-account-key:latest"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan

# Get service URL
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format "value(status.url)"

Write-Host ""
Write-Host "🌐 Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Yellow
Write-Host "1. Open the URL in your browser"
Write-Host "2. Test the questionnaire generation"
Write-Host "3. Monitor logs: gcloud run logs tail $SERVICE_NAME --region $REGION"
Write-Host ""
