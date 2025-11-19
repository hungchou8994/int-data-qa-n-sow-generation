# 🤖 AI Questionnaire & SOW Generator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-FF4B4B.svg)](https://streamlit.io)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-4285F4.svg)](https://cloud.google.com/vertex-ai)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Hệ thống AI tự động sinh **Bảng câu hỏi khảo sát (Questionnaire)** và **Phạm vi công việc (Scope of Work)** cho các dự án tư vấn, tích hợp Google Gemini, RAG (BigQuery Vector Search), và xuất kết quả ra Google Sheets.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Deployment](#-deployment)
- [Project Structure](#-project-structure)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

---

## ✨ Features

### 🎯 Questionnaire Generator
- **AI-Powered Generation**: Sử dụng Google Gemini với RAG để sinh câu hỏi thông minh
- **Multi-Category Support**: Tổ chức câu hỏi theo các danh mục logic (Technical, Business, Infrastructure, etc.)
- **Quality Control**: AI Judge tự động đánh giá chất lượng câu hỏi (coverage, relevance, clarity)
- **Retry Mechanism**: Tự động regenerate nếu chất lượng không đạt (max 3 lần)
- **RAG Integration**: Vector search trên BigQuery để lấy câu hỏi tương tự
- **Google Sheets Export**: Xuất trực tiếp vào Google Sheet với formatting chuyên nghiệp
- **Custom Worksheet**: Người dùng tự đặt tên worksheet, tự động xóa & tạo mới
- **Requirements Display**: Hiển thị yêu cầu gốc của người dùng (truncated 200 chars)

### 📝 SOW Generator
- **Multi-Agent System**: 4 agents chuyên biệt (Generate, Quality, Refine, Export)
- **Intelligent Orchestration**: Judge-based quality control với auto-retry
- **Comprehensive Output**: Project Detail + Assumptions + Scope of Work
- **Professional Formatting**: 15-column task breakdown với man-days, owners, dates
- **Dual Worksheet Export**: 
  - Worksheet 1 "Overview": Project metadata + Detail (left) + Assumptions (right)
  - Worksheet 2 "Scope of Work": Full task table với Progress dropdown
- **Category Grouping**: Tasks grouped by category với auto-calculated totals
- **Interactive UI**: Phase-by-phase generation với real-time status updates

### 🚀 Common Features
- **Streamlit UI**: Modern, responsive web interface
- **Session Management**: Persistent state across interactions
- **JSON Export**: Download results as structured JSON
- **Error Handling**: Comprehensive error reporting và user guidance
- **Cost Tracking**: Token usage monitoring (if implemented)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User (Web Browser)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                            │
│  ┌───────────────────────┐  ┌────────────────────────────────┐ │
│  │ questionnaire_ui.py   │  │    sow_agent_ui.py             │ │
│  │ - Input form          │  │    - 4-phase workflow          │ │
│  │ - Config sidebar      │  │    - Agent orchestration       │ │
│  │ - Export interface    │  │    - Quality control           │ │
│  └───────────────────────┘  └────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Questionnaire Module (app/questionaires/)                 │  │
│  │  - engine.py: Core generation logic                       │  │
│  │  - model.py: Pydantic models (Question, Category, etc.)   │  │
│  │  - prompts.py: LLM prompt templates                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ SOW Module (app/scope_of_work/)                           │  │
│  │  - engine.py: Multi-agent orchestrator                    │  │
│  │  - model.py: SOW data models                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Sheet Connectors (app/sheet/, app/sow_sheet/)             │  │
│  │  - connect.py: Google Sheets API integration              │  │
│  │  - model.py: Sheet operation models                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Google       │  │ BigQuery     │  │ Google Sheets      │   │
│  │ Gemini API   │  │ Vector Search│  │ API                │   │
│  │ (LLM)        │  │ (RAG)        │  │ (Export)           │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Questionnaire Generation:**
```
User Input → RAG Retrieval (BigQuery) → LLM Generation (Gemini)
                                              ↓
                                         AI Judge
                                              ↓
                                    Pass? → Export to Sheets
                                    Fail? → Retry (max 3x)
```

**SOW Generation:**
```
Phase 1: Gather Info → Extract requirements
Phase 2: Generate → Multi-agent system (Generate + Quality + Refine)
Phase 3: Quality Control → Judge evaluation + auto-retry
Phase 4: Export → Dual-worksheet formatting → Google Sheets
```

---

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.11+**: Primary language
- **Streamlit 1.28+**: Web UI framework
- **Pydantic 2.0+**: Data validation

### AI/ML
- **Google Gemini**: LLM for generation (gemini-1.5-flash, gemini-1.5-pro)
- **BigQuery Vector Search**: RAG for retrieval
- **Vertex AI**: ML platform

### Cloud Services
- **Google Cloud Run**: Serverless deployment
- **Secret Manager**: Credential management
- **Cloud Build**: Container builds
- **Artifact Registry**: Docker registry

### APIs & Integrations
- **Google Sheets API**: Export functionality
- **gspread**: Python wrapper for Sheets
- **google-auth**: Authentication

### Development
- **python-dotenv**: Environment variables
- **pytest**: Testing framework
- **black**: Code formatting

---

## 📦 Prerequisites

### 1. Software Requirements
- Python 3.11 or higher
- pip (Python package manager)
- Git
- Google Cloud SDK (for deployment)

### 2. Google Cloud Platform
- **GCP Project** với các API enabled:
  - Vertex AI API (`aiplatform.googleapis.com`)
  - BigQuery API (`bigquery.googleapis.com`)
  - Google Sheets API (`sheets.googleapis.com`)
  - Google Drive API (`drive.googleapis.com`)
  - Secret Manager API (`secretmanager.googleapis.com`)
  - Cloud Run API (`run.googleapis.com`)

### 3. Credentials
- **Google API Key**: Gemini API access
- **Service Account JSON**: BigQuery + Sheets access
  - Required roles:
    - BigQuery Data Viewer
    - BigQuery Job User
    - Vertex AI User

### 4. Google Sheets
- Shared Sheet URL (người dùng cung cấp)
- Service account email added as Editor

---

## 🚀 Installation

### Local Development

1. **Clone repository**
   ```bash
   git clone https://github.com/hungchou8994/int-data-qa-n-sow-generation.git
   cd int-data-qa-n-sow-generation
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   cd app
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   # Create .env file in project root
   cp .env.example .env
   
   # Edit .env with your credentials
   GOOGLE_API_KEY=your_gemini_api_key_here
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
   ```

5. **Verify installation**
   ```bash
   python -c "import streamlit; import google.generativeai; print('OK')"
   ```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Required
GOOGLE_API_KEY=AIzaSy...                    # Gemini API key
GOOGLE_APPLICATION_CREDENTIALS=D:\path\to\service-account.json

# Optional
PROJECT_ID=int-data-qa-n-sow-generation     # GCP project ID
BQ_DATASET=your_dataset                     # BigQuery dataset name
BQ_TABLE=your_table                         # BigQuery table name
```

### Service Account Setup

1. **Create service account** in GCP Console
2. **Grant IAM roles:**
   ```bash
   gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
     --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
     --role=roles/bigquery.dataViewer

   gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
     --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
     --role=roles/bigquery.jobUser

   gcloud projects add-iam-policy-binding int-data-qa-n-sow-generation \
     --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
     --role=roles/aiplatform.user
   ```

3. **Download JSON key** và set trong `.env`

### BigQuery Setup (RAG)

Prepare your questionnaire embeddings table:
```sql
CREATE TABLE `project.dataset.questionnaire_embeddings` (
  id STRING,
  question TEXT,
  embedding ARRAY<FLOAT64>,
  category STRING,
  metadata JSON
);
```

---

## 💻 Usage

### Questionnaire Generator

1. **Start app**
   ```bash
   cd app
   streamlit run questionnaire_ui.py
   ```

2. **Open browser**: http://localhost:8501

3. **Configure (Sidebar)**
   - Google API Key (if not in .env)
   - Model selection (gemini-1.5-flash recommended)
   - Temperature (0.7 default)

4. **Generate questionnaire**
   - Enter customer name
   - Describe business domain
   - Specify requirements
   - Click "Generate Questionnaire"

5. **Export to Google Sheets**
   - Paste Google Sheet URL
   - Enter worksheet name (default: "Questionnaire")
   - Click "Export to Google Sheets"

### SOW Generator

1. **Start app**
   ```bash
   cd app
   streamlit run sow_agent_ui.py
   ```

2. **Phase 1: Gather Information**
   - Customer name
   - Business context
   - Requirements
   - Click "Start Generation"

3. **Phase 2-3: AI Generation** (automatic)
   - Agent system generates SOW
   - Judge evaluates quality
   - Auto-retry if needed

4. **Phase 4: Export**
   - Paste Google Sheet URL
   - Enter worksheet names (default: "Overview", "Scope of Work")
   - Click "Export to Google Sheets"
   - Or download JSON

### Testing SOW Export

```bash
cd app/sow_sheet
python test_export.py
```

---

## 🚢 Deployment

### Quick Deploy to Cloud Run

1. **Setup secrets** (one-time)
   ```powershell
   # Create secrets in Secret Manager
   echo -n "YOUR_API_KEY" | gcloud secrets create google-api-key --data-file=-
   
   gcloud secrets create service-account-key `
     --data-file="D:\path\to\service-account.json"
   
   # Grant access to Cloud Run service account
   .\setup-permissions.ps1
   ```

2. **Deploy**
   ```powershell
   # Windows
   .\deploy.ps1
   
   # Linux/Mac
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Access deployed app**
   - URL will be displayed after deployment
   - Format: `https://SERVICE_NAME-HASH-REGION.run.app`

### Manual Deployment

See detailed guide: [DEPLOYMENT.md](DEPLOYMENT.md)

### Service Account Permissions

See setup guide: [SERVICE_ACCOUNT_SETUP.md](SERVICE_ACCOUNT_SETUP.md)

### Observability (Optional)

See monitoring guide: [OBSERVABILITY.md](OBSERVABILITY.md)

---

## 📁 Project Structure

```
int-data-qa-n-sow-generation/
├── app/                                # Main application
│   ├── questionnaire_ui.py            # Questionnaire Streamlit UI
│   ├── sow_agent_ui.py                # SOW Streamlit UI
│   ├── requirements.txt               # Python dependencies
│   ├── questionaires/                 # Questionnaire module
│   │   ├── engine.py                  # Core generation logic
│   │   ├── model.py                   # Pydantic data models
│   │   ├── prompts.py                 # LLM prompt templates
│   │   └── test.py                    # Unit tests
│   ├── scope_of_work/                 # SOW module
│   │   ├── engine.py                  # Multi-agent orchestrator
│   │   └── model.py                   # SOW data models
│   ├── sheet/                         # Questionnaire sheets connector
│   │   ├── connect.py                 # Google Sheets integration
│   │   └── model.py                   # Sheet models
│   └── sow_sheet/                     # SOW sheets connector
│       ├── connect.py                 # SOW export logic
│       ├── model.py                   # SOW sheet models
│       └── test_export.py             # Export testing script
├── rag/                                # RAG module
│   ├── main.py                        # RAG orchestrator
│   ├── bq_vector.py                   # BigQuery vector search
│   ├── requirements.txt               # RAG dependencies
│   ├── embedding/                     # Embedding generation
│   │   └── model.py                   # Embedding models
│   └── sheet/                         # RAG data ingestion
│       ├── ingest_questionnaires.py   # Ingest questionnaires
│       ├── ingest_sows.py             # Ingest SOWs
│       ├── prompt.py                  # Embedding prompts
│       ├── questionaires.csv          # Sample data
│       └── sow_hung.csv               # Sample SOW data
├── Dockerfile                          # Container definition
├── .dockerignore                       # Docker build exclusions
├── deploy.ps1                          # PowerShell deployment script
├── deploy.sh                           # Bash deployment script
├── setup-permissions.ps1               # IAM permission setup
├── .env.example                        # Environment template
├── .gitignore                          # Git exclusions
├── README.md                           # This file
├── DEPLOYMENT.md                       # Deployment guide
├── SERVICE_ACCOUNT_SETUP.md            # Permission guide
└── OBSERVABILITY.md                    # Monitoring guide
```

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Cloud Run deployment guide
- **[SERVICE_ACCOUNT_SETUP.md](SERVICE_ACCOUNT_SETUP.md)**: IAM permissions setup
- **[OBSERVABILITY.md](OBSERVABILITY.md)**: Monitoring & logging setup

### Key Components

#### Questionnaire Module (`app/questionaires/`)
- **engine.py**: Core generation with retry logic
- **model.py**: Data models (Question, Category, Questionnaire)
- **prompts.py**: System prompts và templates

#### SOW Module (`app/scope_of_work/`)
- **engine.py**: Multi-agent orchestrator (4 agents)
- **model.py**: SOW models (ProjectDetail, ProjectAssumption, ScopeOfWork)

#### Sheet Connectors (`app/sheet/`, `app/sow_sheet/`)
- **connect.py**: Google Sheets API wrapper
- Delete + recreate worksheet approach
- Professional formatting (colors, borders, widths)
- Frozen headers, data validation (dropdowns)

#### RAG Module (`rag/`)
- **bq_vector.py**: BigQuery vector similarity search
- **embedding/model.py**: Text embedding generation
- **sheet/ingest_*.py**: Data ingestion scripts

---

## 🧪 Testing

### Run unit tests
```bash
cd app/questionaires
python -m pytest test.py -v
```

### Test SOW export
```bash
cd app/sow_sheet
python test_export.py
```

### Manual testing checklist
- [ ] Generate questionnaire (5-10 categories)
- [ ] Judge passes (score >= 75)
- [ ] Export to Google Sheets works
- [ ] Worksheet name customization works
- [ ] Generate SOW (all 4 phases)
- [ ] SOW export creates 2 worksheets
- [ ] Formatting is correct (colors, borders, widths)

---

## 🤝 Contributing

### Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Follow PEP 8 style guide
   - Add docstrings to functions
   - Update tests if needed

3. **Test locally**
   ```bash
   streamlit run questionnaire_ui.py
   ```

4. **Commit & push**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**

### Code Style
- Use **black** for formatting: `black app/`
- Use **flake8** for linting: `flake8 app/`
- Follow **PEP 8** conventions

---

## 📊 Performance

### Latency Benchmarks (local)
- **Questionnaire Generation**: 15-30s (depends on RAG retrieval + LLM)
- **SOW Generation**: 45-90s (multi-agent with retries)
- **Sheet Export**: 3-8s (depends on data size)

### Cloud Run Performance
- **Cold start**: 10-15s (first request)
- **Warm start**: 2-5s (subsequent requests)
- **Memory usage**: ~500MB-1GB
- **CPU**: 2 vCPU recommended

---

## 🔒 Security

### Best Practices
- ✅ Never commit `.env` or credentials to git
- ✅ Use Secret Manager for production secrets
- ✅ Rotate API keys regularly
- ✅ Use service accounts with least privilege
- ✅ Enable Cloud Armor (DDoS protection) for production
- ✅ Implement authentication if needed (Cloud IAP, OAuth)

### Secrets Management
- **Local**: `.env` file (gitignored)
- **Cloud Run**: Secret Manager
- **CI/CD**: GitHub Secrets or Cloud Build substitutions

---

## 🐛 Troubleshooting

### Common Issues

**1. Module import error after folder rename**
```bash
# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
# Or Windows PowerShell
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

**2. Google Sheets "Insufficient permissions"**
- Share sheet với service account email (from JSON)
- Grant "Editor" permission

**3. BigQuery "Access Denied"**
- Verify service account has `roles/bigquery.dataViewer`
- Check dataset/table permissions

**4. Gemini API quota exceeded**
- Check API quotas in GCP Console
- Increase quota or use exponential backoff

**5. Streamlit connection error**
```bash
# Disable XSRF protection
streamlit run app.py --server.enableXsrfProtection=false
```

**6. Cloud Run deployment fails**
```bash
# Check build logs
gcloud builds log BUILD_ID

# Check service logs
gcloud run logs tail SERVICE_NAME --region asia-southeast1
```

---


## 🙏 Acknowledgments

- Google Cloud Platform for Vertex AI & BigQuery
- Streamlit team for excellent web framework
- Google Gemini for powerful LLM capabilities

---

## 📞 Support

**Issues & Questions:**
- GitHub Issues: [Create an issue](https://github.com/hungchou8994/int-data-qa-n-sow-generation/issues)
- Email: hung.chou@cloudace.vn

**Documentation:**
- [Google Gemini API Docs](https://ai.google.dev/docs)
- [Streamlit Docs](https://docs.streamlit.io)
- [BigQuery Vector Search](https://cloud.google.com/bigquery/docs/vector-search)

---

## 🗺️ Roadmap

### Version 1.1 (Planned)
- [ ] Migrate to Google ADK (Agent Development Kit)
- [ ] Implement A2A (Agent-to-Agent) communication
- [ ] Add OpenTelemetry observability
- [ ] Custom dashboards in Cloud Monitoring
- [ ] Automated testing pipeline (CI/CD)

### Version 1.2 (Future)
- [ ] Multi-language support (English, Vietnamese)
- [ ] PDF export functionality
- [ ] Template management system
- [ ] User authentication & authorization
- [ ] Team collaboration features

---

<div align="center">



</div>