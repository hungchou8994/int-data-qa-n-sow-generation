# Service Account Permissions Setup

## Current Service Account
- **Email:** `696121145367-compute@developer.gserviceaccount.com`
- **Project:** `int-data-qa-n-sow-generation`

## Required IAM Roles

### 1. Cloud Run Service Agent (Auto-assigned)
```bash
# This is automatically assigned when you deploy to Cloud Run
# Role: roles/run.serviceAgent
```

### 2. BigQuery Permissions (for RAG/Vector Search)
```bash
# BigQuery Data Viewer - Read datasets and tables
gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
  --member="serviceAccount:696121145367-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# BigQuery Job User - Run queries
gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
  --member="serviceAccount:696121145367-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### 3. Vertex AI Permissions (for Gemini API)
```bash
# Vertex AI User - Use Gemini models
gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
  --member="serviceAccount:696121145367-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 4. Secret Manager Permissions (for credentials)
```bash
# Secret Manager Secret Accessor - Read secrets
gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
  --member="serviceAccount:696121145367-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 5. Storage Permissions (if using GCS)
```bash
# Storage Object Viewer - Read files from buckets (optional)
gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
  --member="serviceAccount:696121145367-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

## Grant All Permissions at Once

```powershell
# PowerShell script to grant all required permissions
$PROJECT_ID = "int-data-qa-n-sow-generation"
$SERVICE_ACCOUNT = "696121145367-compute@developer.gserviceaccount.com"

Write-Host "Granting IAM permissions to service account..." -ForegroundColor Yellow

# BigQuery
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/bigquery.jobUser"

# Vertex AI
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/aiplatform.user"

# Secret Manager
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/secretmanager.secretAccessor"

# Storage (optional)
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$SERVICE_ACCOUNT" `
  --role="roles/storage.objectViewer"

Write-Host "✅ All permissions granted successfully!" -ForegroundColor Green
```

## Google Sheets Service Account

**For Google Sheets export feature**, you need a **separate service account** (the one with the JSON key file):

### Service Account: `int-data-qa-n-sow-gen@int-data-qa-n-sow-generation.iam.gserviceaccount.com`

This account needs:
1. **No GCP IAM roles** - It's only for Google Sheets API
2. **Sheets must be shared with this email** - Users share their Google Sheets with this email

**To find the email:**
```powershell
# Extract email from service account JSON
$json = Get-Content "D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json" | ConvertFrom-Json
Write-Host "Google Sheets Service Account Email:" -ForegroundColor Cyan
Write-Host $json.client_email -ForegroundColor Green
```

## Verify Permissions

```bash
# Check current IAM policy
gcloud projects get-iam-policy int-data-qa-n-sow-generation \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:696121145367-compute@developer.gserviceaccount.com" \
  --format="table(bindings.role)"
```

## Enable Required APIs

```powershell
# Enable all required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sheets.googleapis.com
gcloud services enable drive.googleapis.com
```

## Permission Summary

| Feature | Required Role | Purpose |
|---------|--------------|---------|
| **Cloud Run** | `run.serviceAgent` | Deploy and run service (auto) |
| **BigQuery** | `bigquery.dataViewer` | Read questionnaire/SOW data |
| **BigQuery** | `bigquery.jobUser` | Execute vector search queries |
| **Vertex AI** | `aiplatform.user` | Call Gemini 2.0/2.5 models |
| **Secret Manager** | `secretmanager.secretAccessor` | Read API keys and credentials |
| **Storage** | `storage.objectViewer` | Read files (optional) |

## Troubleshooting

### Error: "Permission denied"
```bash
# Check which permissions are missing
gcloud projects get-iam-policy int-data-qa-n-sow-generation \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:696121145367-compute@developer.gserviceaccount.com"
```

### Error: "API not enabled"
```bash
# Enable the missing API
gcloud services enable [API_NAME].googleapis.com
```

### Error: "Cannot access Google Sheet"
- Make sure the sheet is shared with the **Google Sheets service account email**
- Check the service account JSON file is uploaded to Secret Manager correctly

## Security Best Practices

1. **Principle of Least Privilege:** Only grant necessary permissions
2. **Separate Service Accounts:** 
   - Cloud Run service account (Compute Engine default)
   - Google Sheets service account (separate JSON key)
3. **Rotate Keys:** Regularly rotate service account keys
4. **Monitor Access:** Use Cloud Audit Logs to track service account usage
5. **Limit Scope:** Use resource-level IAM when possible instead of project-level

## Next Steps

1. Run the PowerShell script above to grant all permissions
2. Verify permissions with the verification command
3. Enable all required APIs
4. Test deployment with `.\deploy.ps1`
