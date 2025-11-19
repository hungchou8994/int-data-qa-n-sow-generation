# Cloud Run Deployment Guide

## Prerequisites

1. **Google Cloud SDK** installed
   ```bash
   # Check if installed
   gcloud --version
   
   # If not installed, download from:
   # https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate with GCP**
   ```bash
   gcloud auth login
   gcloud config set project int-data-qa-n-sow-generation
   ```

3. **Setup Secrets in Secret Manager**
   
   **GOOGLE_API_KEY:**
   ```bash
   # Create secret
   echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=-
   
   # Grant Cloud Run access
   gcloud secrets add-iam-policy-binding google-api-key \
     --member=serviceAccount:696121145367-compute@developer.gserviceaccount.com \
     --role=roles/secretmanager.secretAccessor
   ```
   
   **Service Account Key (GOOGLE_APPLICATION_CREDENTIALS):**
   ```bash
   # Upload service account JSON
   gcloud secrets create service-account-key \
     --data-file=D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json
   
   # Grant Cloud Run access
   gcloud secrets add-iam-policy-binding service-account-key \
     --member=serviceAccount:696121145367-compute@developer.gserviceaccount.com \
     --role=roles/secretmanager.secretAccessor
   ```

## Deployment Steps

### Option 1: Using PowerShell Script (Recommended for Windows)

```powershell
# Set environment variable (optional - will be stored in Secret Manager)
$env:GOOGLE_API_KEY="YOUR_API_KEY_HERE"

# Run deployment script
.\deploy.ps1
```

### Option 2: Using Bash Script (Linux/Mac)

```bash
# Make script executable
chmod +x deploy.sh

# Set environment variable
export GOOGLE_API_KEY="YOUR_API_KEY_HERE"

# Run deployment script
./deploy.sh
```

### Option 3: Manual Deployment

1. **Build Docker Image**
   ```bash
   gcloud builds submit --tag gcr.io/int-data-qa-n-sow-generation/questionnaire-generator
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy questionnaire-generator \
     --image gcr.io/int-data-qa-n-sow-generation/questionnaire-generator \
     --platform managed \
     --region asia-southeast1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --timeout 300 \
     --max-instances 10 \
     --set-secrets "GOOGLE_API_KEY=google-api-key:latest,GOOGLE_APPLICATION_CREDENTIALS=service-account-key:latest"
   ```

## Update Dockerfile for Multiple Apps

If you want to deploy **both questionnaire_ui.py and sow_agent_ui.py**, modify the Dockerfile:

### Option A: Deploy as separate services

**For Questionnaire Generator:**
```dockerfile
CMD ["streamlit", "run", "questionnaire_ui.py", "--server.port=8080"]
```

Deploy:
```bash
gcloud run deploy questionnaire-generator --image ... --region asia-southeast1
```

**For SOW Generator:**
Change Dockerfile CMD to:
```dockerfile
CMD ["streamlit", "run", "sow_agent_ui.py", "--server.port=8080"]
```

Deploy:
```bash
gcloud run deploy sow-generator --image ... --region asia-southeast1
```

### Option B: Create a launcher page

Create `app/main.py`:
```python
import streamlit as st

st.set_page_config(page_title="Cloud Ace Tools", layout="wide")

st.title("🤖 Cloud Ace AI Tools")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📋 Questionnaire Generator")
    st.markdown("Generate intelligent questionnaires with AI")
    if st.button("Launch Questionnaire Generator", use_container_width=True):
        st.switch_page("pages/questionnaire.py")

with col2:
    st.markdown("### 📝 SOW Generator")
    st.markdown("Generate Scope of Work with AI agents")
    if st.button("Launch SOW Generator", use_container_width=True):
        st.switch_page("pages/sow.py")
```

Then create `pages/` folder and move UI files there.

## Monitoring & Logs

**View logs:**
```bash
gcloud run logs tail questionnaire-generator --region asia-southeast1
```

**Monitor service:**
```bash
gcloud run services describe questionnaire-generator --region asia-southeast1
```

**Get service URL:**
```bash
gcloud run services describe questionnaire-generator \
  --platform managed \
  --region asia-southeast1 \
  --format 'value(status.url)'
```

## Troubleshooting

### 1. Build fails
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Check file paths are correct

### 2. Deployment fails
- Verify secrets exist: `gcloud secrets list`
- Check IAM permissions for Cloud Run service account
- Verify project ID and region

### 3. App doesn't start
- Check logs: `gcloud run logs tail SERVICE_NAME`
- Verify environment variables
- Check port 8080 is exposed

### 4. API errors
- Verify GOOGLE_API_KEY is set correctly
- Check service account has necessary permissions
- Verify BigQuery and Vertex AI APIs are enabled

## Cost Optimization

**Cloud Run Pricing:**
- Memory: 2 GiB
- CPU: 2 vCPU
- Pay only when requests are being processed

**Estimated costs:**
- ~$0.024 per hour when active
- Free tier: First 2 million requests/month

**Tips:**
- Set `--max-instances` to control costs
- Use `--min-instances 0` for cost savings (default)
- Monitor usage in Cloud Console

## Security

1. **Service Account:** Use least privilege principle
2. **Secrets:** Never commit credentials to git
3. **IAM:** Use Secret Manager for sensitive data
4. **Authentication:** Consider adding authentication for production

## Next Steps

After deployment:
1. Test the deployed app thoroughly
2. Set up custom domain (optional)
3. Configure CI/CD pipeline (Cloud Build)
4. Set up monitoring and alerts
5. Configure backup and disaster recovery
