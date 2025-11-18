# AI Questionnaire Generator and SOW Generation System

This project implements an intelligent system for generating questionnaires and Statements of Work (SOW) using AI-powered analysis of historical data and user inputs.

## Project Architecture

The project is organized into two main components:

### 1. Main Application (`/app`)

The main application is a Streamlit-based web interface that handles user interactions and document generation.

#### Components:
- `app.py`: Main application entry point and Streamlit server configuration
- `sow_ui.py`: User interface components and layouts
- `/questionaires`: Module for questionnaire processing
  - `engine.py`: Core questionnaire generation logic
  - `model.py`: Data models and structures
  - `prompts.py`: AI prompt templates and configurations
- `/scope_of_work`: Module for SOW document generation
  - `engine.py`: SOW generation engine
  - `model.py`: SOW data models and templates
- `/sheet`: Module for spreadsheet interactions
  - `connect.py`: Google Sheets integration
  - `model.py`: Spreadsheet data models

### 2. RAG System (`/rag`)

The Retrieval-Augmented Generation (RAG) system handles intelligent document retrieval and context-aware generation.

#### Components:
- `main.py`: RAG system entry point
- `bq_vector.py`: BigQuery vector search implementation
- `/embedding`: Module for text embedding
  - `model.py`: Embedding model implementations
- `/sheet`: Module for data source integration
  - `connect.py`: Google Sheets data source connector
  - `prompt.py`: RAG-specific prompt templates
  - `questionaires.csv`: Historical questionnaire data
  - `questionnaire_embeddings.json`: Pre-computed embeddings

## Technology Stack

- **Frontend**: Streamlit UI framework
- **AI/ML**: Google Generative AI
- **Data Storage**: 
  - Google BigQuery for vector search
  - Google Sheets for data management
- **Core Dependencies**:
  - Python 3.x
  - Streamlit ≥ 1.28.0
  - Google Generative AI ≥ 0.3.0
  - Pandas, NumPy for data processing
  - Pydantic for data validation

## System Flow

1. **User Input Collection**:
   - Web interface captures project requirements
   - Input validation and preprocessing

2. **RAG Processing**:
   - Vector similarity search in historical data
   - Retrieval of relevant past questionnaires and SOWs
   - Context enhancement using embedding models

3. **Document Generation**:
   - AI-powered questionnaire generation
   - SOW document creation based on questionnaire responses
   - Template-based formatting and structure

4. **Data Management**:
   - Integration with Google Sheets for data persistence
   - BigQuery for efficient vector search operations
   - Embedding storage and management






## Project Phases

### Phase 1: Questionnaire Generation ✅ (COMPLETED)

**Objective**: Generate intelligent questionnaires to collect detailed information from clients.

**Input**:
- Client's basic information (name, domain, requirements)
- Target audience
- Project type, budget, timeline (optional)

**Process**:
1. **RAG Retrieval**: Search BigQuery for similar historical questionnaires using vector similarity
2. **AI Generation**: Use Gemini AI to generate contextual questions based on:
   - Client requirements
   - Retrieved similar questions
   - Domain expertise
3. **Feedback Loop**: Support regeneration with user feedback

**Output**:
- Comprehensive questionnaire (15-20 questions)
- Organized by sections (Background, Process, Data, Timeline, etc.)
- Available in multiple languages (English, Vietnamese)

**Key Features**:
- RAG-based intelligent question generation
- Customizable configuration (number of questions, temperature, retrieval top-K)
- Fallback mechanism for reliability
- Export to JSON and Google Sheets
- Regeneration with feedback

**UI**: `app/sow_ui.py`

---

### Phase 2: SOW Generation ✅ (COMPLETED)

**Objective**: Generate comprehensive Scope of Work documents including Project Details and Project Assumptions.

#### 2.1 Generate Project Detail

**Input**:
- Client information (from Phase 1)
- Questionnaire answers (filled by client)

**Output**:
- **Overview**: 2-3 paragraph project summary
- **Objectives**: 4-8 SMART objectives
- **Scope Summary**: Clear boundaries (in-scope and out-of-scope)
- **Key Features**: 5-10 major capabilities
- **Deliverables**: Tangible outputs and documents

#### 2.2 Generate Project Assumptions

**Input**:
- Client information
- Questionnaire answers
- Project Detail (from step 2.1)

**Output** (5 categories):
- **Technical Assumptions**: Infrastructure, integrations, security
- **Business Assumptions**: Stakeholder availability, processes
- **Resource Assumptions**: Team, skills, tools
- **Timeline Assumptions**: Milestones, dependencies
- **Risk Assumptions**: Potential issues and mitigation

**Key Features**:
- Professional, client-ready documents
- Context-aware generation based on questionnaire responses
- Feedback loop for both Project Detail and Assumptions
- Export to JSON (individual or combined package)
- Multi-language support

**UI**: `app/sow_phase2_ui.py`

---

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: QUESTIONNAIRE GENERATION                           │
├─────────────────────────────────────────────────────────────┤
│ Input: Client Info (Name, Domain, Requirements)            │
│   ↓                                                          │
│ RAG: Search Similar Questions in BigQuery                   │
│   ↓                                                          │
│ LLM: Generate Contextual Questionnaire (Gemini AI)         │
│   ↓                                                          │
│ Output: 15-20 Questions organized by sections               │
│   ↓                                                          │
│ Send to Client → Client fills questionnaire                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: SOW GENERATION                                     │
├─────────────────────────────────────────────────────────────┤
│ Step 1: Generate Project Detail                            │
│ Input: Client Info + Questionnaire Answers                 │
│   ↓                                                          │
│ LLM: Generate Overview, Objectives, Scope, Features        │
│   ↓                                                          │
│ Output: Comprehensive Project Detail Document              │
│                                                              │
│ Step 2: Generate Project Assumptions                       │
│ Input: Client Info + Answers + Project Detail              │
│   ↓                                                          │
│ LLM: Generate 5 Categories of Assumptions                  │
│   ↓                                                          │
│ Output: Technical, Business, Resource, Timeline, Risk      │
│                                                              │
│ Export: Complete SOW Package (JSON)                        │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r app/requirements.txt

# Set environment variables
GOOGLE_API_KEY=your-gemini-api-key
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### Run Phase 1 (Questionnaire Generation)
```bash
cd app
streamlit run sow_ui.py
```

### Run Phase 2 (SOW Generation)
```bash
cd app
streamlit run sow_phase2_ui.py
```

### Run Tests
```bash
# Test Phase 1
cd app/questionaires
python test.py

# Test Phase 2
cd app/scope_of_work
python test.py
```

## File Structure

```
int-data-qa-n-sow-generation/
├── app/
│   ├── sow_ui.py                    # Phase 1 UI
│   ├── sow_phase2_ui.py             # Phase 2 UI (NEW)
│   ├── questionaires/               # Phase 1 Module
│   │   ├── engine.py
│   │   ├── model.py
│   │   ├── prompts.py
│   │   └── test.py
│   └── scope_of_work/               # Phase 2 Module (NEW)
│       ├── engine.py                # SOW generation logic
│       ├── model.py                 # Data models
│       ├── prompts.py               # System prompts
│       ├── test.py                  # Test script
│       ├── sample_questionnaire_answers.json
│       └── README.md
├── rag/                             # RAG System
│   ├── bq_vector.py                 # BigQuery vector search
│   ├── main.py
│   └── sheet/
│       ├── ingest_questionnaires.py
│       └── ingest_sows.py
└── .env                             # Configuration
```

## Features Comparison

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| **Input** | Client basic info | Client info + Questionnaire answers |
| **RAG** | ✅ BigQuery vector search | ❌ Direct LLM (future enhancement) |
| **LLM** | Gemini 2.5 Flash | Gemini 2.0 Flash Exp |
| **Output** | Questionnaire (15-20 questions) | Project Detail + Assumptions |
| **Feedback Loop** | ✅ Regenerate with feedback | ✅ Regenerate with feedback |
| **Export** | JSON, Google Sheets | JSON (individual or package) |
| **Multi-language** | ✅ English, Vietnamese | ✅ English, Vietnamese |
| **UI** | Streamlit (3 tabs) | Streamlit (3 tabs) |

