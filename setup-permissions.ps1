# Grant all required IAM permissions to Cloud Run service account
# Run this script before deploying to Cloud Run

$PROJECT_ID = "int-data-qa-n-sow-generation"
$SERVICE_ACCOUNT = "696121145367-compute@developer.gserviceaccount.com"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Service Account Permissions Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ID"
Write-Host "Service Account: $SERVICE_ACCOUNT"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Enable required APIs
Write-Host "🔧 Enabling required APIs..." -ForegroundColor Yellow
$apis = @(
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "sheets.googleapis.com",
    "drive.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "  - Enabling $api"
    gcloud services enable $api --project=$PROJECT_ID
}

Write-Host "✅ APIs enabled" -ForegroundColor Green
Write-Host ""

# Grant IAM permissions
Write-Host "🔐 Granting IAM permissions..." -ForegroundColor Yellow

$roles = @(
    @{Name="BigQuery Data Viewer"; Role="roles/bigquery.dataViewer"},
    @{Name="BigQuery Job User"; Role="roles/bigquery.jobUser"},
    @{Name="Vertex AI User"; Role="roles/aiplatform.user"},
    @{Name="Secret Manager Secret Accessor"; Role="roles/secretmanager.secretAccessor"},
    @{Name="Storage Object Viewer"; Role="roles/storage.objectViewer"}
)

foreach ($roleInfo in $roles) {
    Write-Host "  - Granting $($roleInfo.Name) ($($roleInfo.Role))"
    gcloud projects add-iam-policy-binding $PROJECT_ID `
      --member="serviceAccount:$SERVICE_ACCOUNT" `
      --role="$($roleInfo.Role)" `
      --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ Success" -ForegroundColor Green
    } else {
        Write-Host "    ❌ Failed" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ All permissions granted!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verify permissions
Write-Host "📋 Verifying permissions..." -ForegroundColor Yellow
Write-Host ""
gcloud projects get-iam-policy $PROJECT_ID `
  --flatten="bindings[].members" `
  --filter="bindings.members:serviceAccount:$SERVICE_ACCOUNT" `
  --format="table(bindings.role)"

Write-Host ""
Write-Host "✅ Setup complete! You can now deploy to Cloud Run." -ForegroundColor Green
Write-Host ""
