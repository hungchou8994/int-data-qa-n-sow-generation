# SOW Agent System - Complete Documentation

## 🎯 Overview

This is an **AI-Agent-based SOW Generation System** that automatically creates comprehensive project documentation with **built-in quality control** and **intelligent cascade regeneration**.

### Key Features
- ✅ **Automated Quality Control**: LLM-as-a-Judge validates each component
- ✅ **RAG-Enhanced**: Retrieves similar tasks from past projects (BigQuery Vector Search)
- ✅ **Cascade Regeneration**: Smart dependency-aware regeneration on feedback
- ✅ **Multi-Stage Workflow**: Input → Auto-Generation → Human Review → Approval
- ✅ **Version Tracking**: Full audit trail of all generations and feedback

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: AUTO-CORRECTION                  │
│                                                               │
│  Generate PD → Judge PD → [PASS? Yes → Next]                │
│                         └─ [FAIL? → Regen max 3x]           │
│                                                               │
│  Generate PA → Judge PA → [PASS? Yes → Next]                │
│    (uses PD)          └─ [FAIL? → Regen max 3x]             │
│                                                               │
│  Generate SoW → Judge SoW → [PASS? Yes → Phase 2]           │
│    (uses PD+PA+RAG)     └─ [FAIL? → Regen max 3x]          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 2: HUMAN REVIEW                     │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ Project Detail  │  │ Project Assume. │  │ Scope of Work││
│  │                 │  │                 │  │              ││
│  │ [Feedback Box]  │  │ [Feedback Box]  │  │[Feedback Box]││
│  │ [Regenerate]    │  │ [Regenerate]    │  │[Regenerate]  ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
│                                                               │
│              [✅ APPROVE ALL COMPONENTS]                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   PHASE 3: CASCADE REGEN                     │
│                                                               │
│  IF target = "Project Detail":                               │
│    → Regen PD → Judge → Regen PA → Judge → Regen SoW → Judge│
│                                                               │
│  IF target = "Project Assumption":                           │
│    → Keep PD → Regen PA → Judge → Regen SoW → Judge         │
│                                                               │
│  IF target = "Scope of Work":                                │
│    → Keep PD, PA → Regen SoW → Judge                         │
│                                                               │
│  → Return to PHASE 2 for review                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 4: APPROVED                        │
│                                                               │
│  - Lock all components                                        │
│  - Export as JSON                                             │
│  - Save to database/Google Sheets                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
app/scope_of_work/
├── model.py              # Data models (ProjectDetail, ProjectAssumption, ScopeOfWork, etc.)
├── engine.py             # SOWEngine - LLM generation for all 3 components
├── judge.py              # SOWJudge - Quality control with 3 rubrics
├── orchestrator.py       # SOWOrchestrator - Manages workflow & cascade logic
├── prompts.py            # System prompts for all components
├── sheet_reader.py       # Google Sheets integration
└── README.md             # Documentation

app/
├── sow_agent_ui.py       # Main Streamlit UI (NEW AGENT SYSTEM)
└── sow_phase2_ui.py      # Old UI (simple generate + feedback)

rag/
└── bq_vector.py          # BigQuery Vector Search for RAG
```

---

## 🔧 Setup & Installation

### 1. Prerequisites
- Python 3.8+
- Google Cloud Project with BigQuery
- Service Account with permissions:
  - BigQuery Data Editor
  - BigQuery Job User
  - Vertex AI User (for embeddings)

### 2. Install Dependencies

```bash
pip install -r app/requirements.txt
```

**Key packages:**
- `streamlit` - UI framework
- `google-generativeai` - Gemini API
- `google-cloud-bigquery` - BigQuery client
- `gspread` - Google Sheets API
- `python-dotenv` - Environment variables

### 3. Environment Variables

Create `.env` file:

```env
# Gemini API
GOOGLE_API_KEY=AIzaSy...

# Google Cloud
PROJECT_NUMBER=696121145367
GOOGLE_APPLICATION_CREDENTIALS=D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json
```

### 4. BigQuery Setup

Your BigQuery dataset should have:

**Table: `sow_tasks_embedded`**
```sql
CREATE TABLE `qa_sow_dataset.sow_tasks_embedded` (
  prj_id STRING,
  project_type STRING,
  task_category STRING,
  task_title STRING,
  content STRING,
  man_days FLOAT64,
  embedding ARRAY<FLOAT64>
);
```

**Embedding Model:**
```sql
CREATE MODEL `qa_sow_dataset.gemini_embedding_model`
REMOTE WITH CONNECTION `your_connection`
OPTIONS (
  endpoint = 'gemini-1.5-flash'
);
```

---

## 🚀 Usage

### Run the Agent UI

```bash
cd app
streamlit run sow_agent_ui.py
```

### Workflow Steps

**STEP 1: Input**
1. Fill in client information (name, domain, requirements, etc.)
2. Provide questionnaire answers via:
   - Google Sheets URL
   - JSON file upload
   - Manual entry
3. Click **"START SOW GENERATION"**

**STEP 2: Auto-Generation (PHASE 1)**
- System generates all 3 components automatically
- Each component is validated by Judge
- Auto-retry up to 3 times if FAIL
- Takes 2-5 minutes (3 components × 3 LLM calls each = ~9 API calls)

**STEP 3: Human Review (PHASE 2)**
- Review all 3 components in tabs
- See judge scores and feedback
- Provide feedback for any component
- Click **"Regenerate"** to improve
- Cascade regeneration happens automatically
- Repeat until satisfied

**STEP 4: Approval (PHASE 4)**
- Click **"APPROVE ALL COMPONENTS"**
- Download as JSON
- Start new generation if needed

---

## 🧠 AI Components

### 1. SOWEngine (Generator)
**Location:** `scope_of_work/engine.py`

**Methods:**
- `generate_project_detail()` - Creates project overview + key features
- `generate_project_assumption()` - Creates assumptions (Data Scope, SoW, domain-specific)
- `generate_scope_of_work()` - Creates task breakdown with RAG

**LLM Model:** `gemini-2.5-flash` (for generation)

### 2. SOWJudge (Quality Control)
**Location:** `scope_of_work/judge.py`

**Rubrics:**

**Project Detail (100 points):**
- Accuracy & Alignment (40 pts)
- Completeness & Detail (30 pts)
- Specificity & Clarity (20 pts)
- Structure & Format (10 pts)

**Project Assumption (100 points):**
- Consistency with PD (35 pts)
- Completeness of Sections (25 pts)
- Specificity & Measurability (25 pts)
- Clarity & Professional Quality (15 pts)

**Scope of Work (100 points):**
- Consistency with PA (30 pts)
- Coverage of RAG Tasks (25 pts)
- Completeness & Detail (25 pts)
- Specificity & Realism (20 pts)

**Pass Threshold:** 75/100 (configurable in UI)

**LLM Model:** `gemini-2.0-flash-exp` (for judging)

### 3. SOWOrchestrator (Workflow Manager)
**Location:** `scope_of_work/orchestrator.py`

**Key Methods:**
- `generate_complete_sow()` - PHASE 1 auto-correction loop
- `handle_feedback()` - PHASE 3 cascade regeneration

**Cascade Logic:**
```python
if target == "project_detail":
    # Full cascade
    new_PD = regenerate_PD(feedback)
    new_PA = regenerate_PA(new_PD)  # Cascade
    new_SoW = regenerate_SoW(new_PD, new_PA)  # Cascade

elif target == "project_assumption":
    # PA + SoW cascade
    new_PA = regenerate_PA(feedback)
    new_SoW = regenerate_SoW(old_PD, new_PA)  # Cascade

elif target == "scope_of_work":
    # No cascade
    new_SoW = regenerate_SoW(feedback)
```

---

## 🎯 Key Design Decisions

### Why LLM-as-a-Judge?
- **Problem:** LLMs can generate inconsistent or low-quality output
- **Solution:** Second LLM evaluates first LLM's output with strict rubrics
- **Benefit:** Automated quality control without human intervention in PHASE 1

### Why Cascade Regeneration?
- **Problem:** Components are interdependent (PA depends on PD, SoW depends on both)
- **Solution:** When upstream component changes, downstream must regenerate
- **Benefit:** Maintains consistency across all components

### Why Version Tracking?
- **Problem:** Users might want to rollback or compare versions
- **Solution:** `ComponentVersion` dataclass stores each generation with metadata
- **Benefit:** Full audit trail of all changes and feedback

### Why RAG for SoW?
- **Problem:** Generating realistic task breakdowns from scratch is difficult
- **Solution:** Retrieve similar tasks from past projects, then adapt to current context
- **Benefit:** More accurate man-day estimates and comprehensive task coverage

---

## 📊 Data Models

### Core Models

**ProjectDetail**
```python
{
    "detail_id": "uuid",
    "customer_name": "ABC Company",
    "overview": "This is a project about...",
    "key_features": [
        "1. Feature Title\n- Bullet 1\n- Bullet 2",
        "2. Another Feature\n- Bullet 1\n- Bullet 2"
    ],
    "created_at": "2025-10-30T10:00:00",
    "language": "English"
}
```

**ProjectAssumption**
```python
{
    "assumption_id": "uuid",
    "customer_name": "ABC Company",
    "assumptions": [
        {
            "section": "Data Scope",
            "points": [
                "Client will grant access to Dropbox folders",
                "Data will be complete and accurate"
            ]
        },
        {
            "section": "SoW",
            "points": [
                "This is MVP version only",
                "Production scaling in future phase"
            ]
        }
    ],
    "created_at": "2025-10-30T10:05:00"
}
```

**ScopeOfWork**
```python
{
    "sow_id": "uuid",
    "customer_name": "ABC Company",
    "project_type": "Data Analytics",
    "tasks": [
        {
            "task_category": "Data Integration",
            "task_title": "Automated Daily Data Ingestion",
            "content": "Develop pipeline to collect data from Dropbox...",
            "man_days": 5.0,
            "source": "rag",  # or "generated"
            "similarity_score": 0.87
        }
    ],
    "total_man_days": 120.5,
    "total_tasks": 25,
    "created_at": "2025-10-30T10:10:00"
}
```

**JudgeResult**
```python
{
    "component": "project_detail",
    "status": "PASS",  # or "FAIL"
    "score": 85.0,  # 0-100
    "feedback": "Strong alignment with requirements...",
    "issues": [
        "Feature 3 could be more specific",
        "Consider adding security details"
    ],
    "created_at": "2025-10-30T10:01:00"
}
```

---

## 🧪 Testing

### Manual Testing Checklist

**PHASE 1 (Auto-Correction):**
- [ ] All 3 components generate successfully
- [ ] Judge scores ≥ 75 for all components
- [ ] If score < 75, auto-retry triggers (max 3 times)
- [ ] If still failing after 3 retries, user sees error message

**PHASE 2 (Human Review):**
- [ ] All 3 components display correctly in tabs
- [ ] Judge results show with correct status (PASS/FAIL)
- [ ] Feedback boxes accept text input
- [ ] Regenerate buttons trigger regeneration

**PHASE 3 (Cascade):**
- [ ] Regenerating PD → PA and SoW also regenerate
- [ ] Regenerating PA → only SoW regenerates (PD unchanged)
- [ ] Regenerating SoW → no cascade (PD and PA unchanged)
- [ ] New versions have higher scores

**PHASE 4 (Approval):**
- [ ] Approve button locks components
- [ ] JSON export contains all data
- [ ] Start new generation clears session state

**RAG Integration:**
- [ ] SoW tasks include tasks from BigQuery
- [ ] Tasks are marked as "rag" or "generated"
- [ ] Similarity scores are shown
- [ ] RAG tasks are adapted to project context (not copied blindly)

### Run Test Script

```bash
cd app/scope_of_work
python test.py
```

---

## 🐛 Troubleshooting

### Issue: "API Key not found"
**Solution:** Check `.env` file has `GOOGLE_API_KEY=...`

### Issue: "BigQuery connection failed"
**Solution:** 
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Check service account has BigQuery permissions

### Issue: "No similar tasks retrieved (RAG)"
**Solution:**
- Check `sow_tasks_embedded` table has data
- Verify embedding model exists: `qa_sow_dataset.gemini_embedding_model`
- Run ingestion script to populate table

### Issue: "Judge always returns FAIL"
**Solution:**
- Lower pass threshold in sidebar (from 75 to 60)
- Check judge rubric is not too strict
- Review judge feedback to understand issues

### Issue: "Cascade regeneration not working"
**Solution:**
- Check orchestrator logs for errors
- Verify `handle_feedback()` receives correct `target_component`
- Ensure session state stores current versions

---



## 🔮 Future Enhancements

1. **Multi-LLM Support**: Add option to use GPT-4, Claude, etc.
2. **Custom Rubrics**: Allow users to define their own judge criteria
3. **Parallel Generation**: Generate PD, PA, SoW in parallel (no dependency)
4. **Google Sheets Export**: Auto-publish to Google Sheets template
5. **History Browser**: View all past generations with filtering
6. **A/B Testing**: Compare outputs from different LLM models
7. **Batch Processing**: Generate SOWs for multiple projects at once
8. **API Endpoint**: REST API for integration with other systems

---

## 📖 Complete Generation Workflow (Code-Level Details)

### PHASE 1: Auto-Correction Loop

**Orchestrator Method:** `generate_complete_sow(client_info, questionnaire_answers, config)`

**Sequential Process:**

#### Step 1: Generate Project Detail
```python
# Loop up to max_auto_retries (default 3)
for attempt in range(max_auto_retries):
    # 1.1 Generate with LLM
    input_data = ProjectDetailInput(client_info, questionnaire_answers)
    project_detail = engine.generate_project_detail(input_data, config)
    
    # 1.2 Judge quality
    judge_result = judge.judge_project_detail(
        project_detail, client_info, questionnaire_answers
    )
    
    # 1.3 Check result
    if judge_result.status == "PASS" and judge_result.score >= 75:
        save_to_history(project_detail, version="v_final_auto")
        break  # Proceed to Step 2
    else:
        logger.warning(f"Attempt {attempt+1} FAILED: Score {judge_result.score}/100")
        # Loop continues with regeneration
        
# If all attempts fail:
return OrchestrationResult(
    status="failure",
    failed_component="project_detail",
    error_message=f"Failed after {max_auto_retries} attempts"
)
```

**Key Points:**
- **Input:** Client info + Questionnaire answers only
- **LLM Model:** Gemini 2.0 Flash Exp
- **Output:** ProjectDetail object with `overview` + `key_features[]`
- **Judge Rubric:** 100 points (Accuracy 40, Completeness 30, Specificity 20, Format 10)
- **Pass Threshold:** ≥ 75/100
- **Max Retries:** 3 attempts
- **On Success:** Save to `detail_history` with version `v_final_auto`
- **On Failure:** Return error, stop workflow

#### Step 2: Generate Project Assumption
```python
# Uses PASSED Project Detail from Step 1
for attempt in range(max_auto_retries):
    # 2.1 Generate with LLM (depends on PD)
    input_data = ProjectAssumptionInput(
        client_info, questionnaire_answers, project_detail  # <-- Uses Step 1 output
    )
    project_assumption = engine.generate_project_assumption(input_data, config)
    
    # 2.2 Judge quality (checks consistency with PD)
    judge_result = judge.judge_project_assumption(
        project_assumption, project_detail, client_info, questionnaire_answers
    )
    
    # 2.3 Check result
    if judge_result.status == "PASS" and judge_result.score >= 75:
        save_to_history(project_assumption, version="v_final_auto")
        break  # Proceed to Step 3
    else:
        logger.warning(f"Attempt {attempt+1} FAILED: Score {judge_result.score}/100")
        # Loop continues

# If all attempts fail:
return OrchestrationResult(
    status="partial_failure",
    project_detail=project_detail,  # Step 1 succeeded
    failed_component="project_assumption"
)
```

**Key Points:**
- **Input:** Client info + Questionnaire + **Project Detail (from Step 1)**
- **Dependency:** MUST have valid PD before generating PA
- **Output:** ProjectAssumption object with dynamic `assumptions[]` (sections + points)
- **Judge Rubric:** 100 points (Consistency with PD 35, Completeness 25, Specificity 25, Clarity 15)
- **Critical Check:** Judge verifies PA is consistent with PD
- **On Success:** Save to `assumption_history` with version `v_final_auto`
- **On Failure:** Return partial_failure (PD succeeded, PA failed)

#### Step 3: Generate Scope of Work (with RAG)
```python
# Uses PASSED PD + PA from Steps 1-2
for attempt in range(max_auto_retries):
    # 3.1 Build RAG query from PD + PA
    query = engine._build_rag_query(client_info, project_detail, project_assumption)
    
    # 3.2 Retrieve similar tasks from BigQuery
    rag_tasks = retrieve_similar_sow_tasks(
        query, 
        top_k=20,  # Retrieve 20 most similar tasks
        credentials_path=GOOGLE_APPLICATION_CREDENTIALS
    )
    # Returns: [{'task_category', 'task_title', 'content', 'man_days', 'similarity_score'}]
    
    # 3.3 Generate with LLM (uses RAG context)
    input_data = ScopeOfWorkInput(
        client_info, questionnaire_answers, 
        project_detail, project_assumption  # <-- Uses Steps 1-2 outputs
    )
    scope_of_work = engine.generate_scope_of_work(input_data, config)
    # LLM receives:
    # - Client info + Questionnaire
    # - Project Detail (features)
    # - Project Assumption (constraints)
    # - RAG tasks (20 similar tasks from past projects)
    
    # 3.4 Auto-format task content (add line breaks)
    for task in scope_of_work.tasks:
        # Split by '. ' and join with '.\n\n' for readability
        task.content = format_content_with_line_breaks(task.content)
    
    # 3.5 Judge quality (checks consistency with PA + RAG coverage)
    judge_result = judge.judge_scope_of_work(
        scope_of_work, project_assumption, project_detail, rag_tasks
    )
    
    # 3.6 Check result
    if judge_result.status == "PASS" and judge_result.score >= 75:
        save_to_history(scope_of_work, version="v_final_auto")
        break  # PHASE 1 complete
    else:
        logger.warning(f"Attempt {attempt+1} FAILED: Score {judge_result.score}/100")

# If all attempts fail:
return OrchestrationResult(
    status="partial_failure",
    project_detail=project_detail,     # Step 1 succeeded
    project_assumption=project_assumption,  # Step 2 succeeded
    failed_component="scope_of_work"
)
```

**Key Points:**
- **Input:** Client info + Questionnaire + **PD + PA** + **RAG tasks**
- **RAG Process:**
  1. Build search query from client industry + PD features + PA constraints
  2. Query BigQuery with vector similarity search (cosine distance)
  3. Retrieve top 20 most similar tasks with scores
  4. Pass to LLM as context (NOT rigid templates)
- **Output:** ScopeOfWork object with `tasks[]` (each has category, title, content, man_days, source)
- **Task Sources:**
  - `source="rag"`: Task adapted from RAG retrieval
  - `source="generated"`: Task created by LLM specifically for this project
- **Content Formatting:** Auto-split sentences by `. ` and add `\n\n` for readability
- **Judge Rubric:** 100 points (Consistency with PA 30, RAG Coverage 25, Completeness 25, Realism 20)
- **Critical Checks:**
  - Tasks align with PA constraints (e.g., MVP scope, data limits)
  - RAG tasks are adapted, not blindly copied
  - Man-days are realistic
- **On Success:** Return complete OrchestrationResult with all 3 components
- **On Failure:** Return partial_failure (PD + PA succeeded, SoW failed)

**PHASE 1 Success Criteria:**
```python
return OrchestrationResult(
    status="success",
    project_detail=project_detail,           # Score ≥ 75
    project_assumption=project_assumption,   # Score ≥ 75
    scope_of_work=scope_of_work,            # Score ≥ 75
    detail_judge=JudgeResult(...),
    assumption_judge=JudgeResult(...),
    sow_judge=JudgeResult(...),
    detail_version="v_final_auto",
    assumption_version="v_final_auto",
    sow_version="v_final_auto"
)
```

---

### PHASE 2: Human Review

**UI Component:** `sow_agent_ui.py` → `render_phase2_human_review()`

**Display:**
- 3 tabs: Project Detail, Project Assumptions, Scope of Work
- Each tab shows:
  - Component content (formatted display)
  - Judge score + feedback
  - Feedback text box (for human input)
  - Regenerate button (triggers PHASE 3)
- Global "Approve All" button (moves to PHASE 4)

**User Actions:**
1. Review all 3 components
2. Provide feedback if changes needed
3. Click "Regenerate" for specific component
4. Or click "Approve All" if satisfied

---

### PHASE 3: Cascade Regeneration

**Orchestrator Method:** `handle_feedback(target_component, feedback, current_detail, current_assumption, current_sow, ...)`

**Cascade Logic (Dependency-Aware):**

#### Case 1: Feedback on Project Detail (Full Cascade)
```python
# User provides feedback on Project Detail
target_component = "project_detail"
feedback = "Add more details about security features"

# Step 1: Regenerate PD with feedback (with retry loop)
for attempt in range(max_auto_retries):  # Default 3 attempts
    new_detail = engine.regenerate_project_detail(
        feedback=feedback,
        previous_detail=current_detail,  # LLM sees old version + feedback
        client_info=client_info,
        questionnaire_answers=questionnaire_answers
    )
    judge_result = judge.judge_project_detail(new_detail, ...)
    
    if judge_result.status == "PASS":
        break  # Success, proceed to cascade
    else:
        logger.warning(f"Attempt {attempt+1} FAILED (Score: {judge_result.score}/100)")
        # Add judge issues to feedback for next attempt
        feedback += "\n\nPrevious issues:\n" + "\n".join(judge_result.issues)
        # Retry...

# If all attempts fail, return error to user
if judge_result.status == "FAIL":
    return error_result

# Step 2: CASCADE to PA (because PA depends on PD)
logger.info("Cascading to Project Assumption...")
new_assumption = engine.generate_project_assumption(
    # NO feedback for PA, just regenerate based on new PD
    project_detail=new_detail,  # <-- Uses NEW PD
    client_info=client_info,
    questionnaire_answers=questionnaire_answers
)
judge_result = judge.judge_project_assumption(new_assumption, new_detail, ...)

# Step 3: CASCADE to SoW (because SoW depends on both PD + PA)
logger.info("Cascading to Scope of Work...")
new_sow = engine.generate_scope_of_work(
    project_detail=new_detail,      # <-- Uses NEW PD
    project_assumption=new_assumption,  # <-- Uses NEW PA
    client_info=client_info,
    questionnaire_answers=questionnaire_answers
)
judge_result = judge.judge_scope_of_work(new_sow, ...)

# Save all 3 with new version
version = f"v_human_{version_number}"
save_to_history(new_detail, new_assumption, new_sow, version)

return OrchestrationResult(
    project_detail=new_detail,        # NEW
    project_assumption=new_assumption,  # NEW (cascaded)
    scope_of_work=new_sow,            # NEW (cascaded)
    detail_version=version,
    assumption_version=version,
    sow_version=version
)
```

**Why Full Cascade?**
- PA is generated FROM PD (uses PD's features to create assumptions)
- SoW is generated FROM PD + PA (uses both for task breakdown)
- If PD changes → PA must update → SoW must update
- Ensures consistency across all 3 components

**Retry Mechanism:**
- Each regeneration attempts up to 3 times (configurable)
- If attempt fails judge, feedback is enhanced with judge issues
- If all attempts fail, user sees error message
- Cascaded components (PA, SoW) also have retry loops

#### Case 2: Feedback on Project Assumption (Partial Cascade)
```python
# User provides feedback on Project Assumption
target_component = "project_assumption"
feedback = "Change data scope assumption to 5000 SKUs instead of 1000"

# Step 1: Regenerate PA with feedback (with retry loop)
for attempt in range(max_auto_retries):
    new_assumption = engine.regenerate_project_assumption(
        feedback=feedback,
        previous_assumption=current_assumption,  # LLM sees old + feedback
        project_detail=current_detail,  # <-- Keep EXISTING PD (no change)
        client_info=client_info,
        questionnaire_answers=questionnaire_answers
    )
    judge_result = judge.judge_project_assumption(new_assumption, current_detail, ...)
    
    if judge_result.status == "PASS":
        break
    else:
        # Retry with enhanced feedback
        feedback += "\n\nPrevious issues:\n" + "\n".join(judge_result.issues)

# Step 2: CASCADE to SoW only (SoW depends on PA)
for attempt in range(max_auto_retries):
    logger.info("Cascading to Scope of Work...")
    new_sow = engine.generate_scope_of_work(
        project_detail=current_detail,     # <-- Keep EXISTING PD
        project_assumption=new_assumption,  # <-- Uses NEW PA
        client_info=client_info,
        questionnaire_answers=questionnaire_answers
    )
    judge_result = judge.judge_scope_of_work(new_sow, ...)
    
    if judge_result.status == "PASS":
        break

# Save PA + SoW with new version (PD unchanged)
version = f"v_human_{version_number}"
save_to_history(new_assumption, new_sow, version)

return OrchestrationResult(
    project_detail=current_detail,    # UNCHANGED (reuse existing)
    project_assumption=new_assumption,  # NEW
    scope_of_work=new_sow,            # NEW (cascaded)
    detail_version=previous_version,  # Old version
    assumption_version=version,
    sow_version=version
)
```

**Why Partial Cascade?**
- PA change doesn't affect PD (PD is upstream)
- But SoW depends on PA (must regenerate to reflect new assumptions)
- Saves time by not regenerating PD

**Retry Behavior:**
- PA regeneration: Up to 3 attempts
- SoW cascade: Also up to 3 attempts (independent retry)

#### Case 3: Feedback on Scope of Work (No Cascade)
```python
# User provides feedback on Scope of Work
target_component = "scope_of_work"
feedback = "Add more tasks for testing and QA"

# Step 1: Regenerate SoW only (with retry loop)
for attempt in range(max_auto_retries):
    new_sow = engine.regenerate_scope_of_work(
        feedback=feedback,
        previous_sow=current_sow,  # LLM sees old tasks + feedback
        project_detail=current_detail,     # <-- Keep EXISTING PD
        project_assumption=current_assumption,  # <-- Keep EXISTING PA
        client_info=client_info,
        questionnaire_answers=questionnaire_answers
    )
    judge_result = judge.judge_scope_of_work(new_sow, current_assumption, current_detail, ...)
    
    if judge_result.status == "PASS":
        break
    else:
        logger.warning(f"Attempt {attempt+1} FAILED")
        feedback += "\n\nPrevious issues:\n" + "\n".join(judge_result.issues)

# NO CASCADE (nothing depends on SoW)

# Save SoW only with new version (PD + PA unchanged)
version = f"v_human_{version_number}"
save_to_history(new_sow, version)

return OrchestrationResult(
    project_detail=current_detail,      # UNCHANGED
    project_assumption=current_assumption,  # UNCHANGED
    scope_of_work=new_sow,              # NEW
    detail_version=previous_version,
    assumption_version=previous_version,
    sow_version=version
)
```

**Why No Cascade?**
- SoW is downstream (nothing depends on it)
- Changing SoW doesn't affect PD or PA
- Most efficient regeneration (only 1 component)

**Retry Behavior:**
- SoW regeneration: Up to 3 attempts
- Each attempt accumulates judge feedback
- If all fail, user sees error and can try different feedback

**Cascade Dependency Graph:**
```
Project Detail (PD)
    ↓ (PA depends on PD)
Project Assumption (PA)
    ↓ (SoW depends on PD + PA)
Scope of Work (SoW)

Regeneration Impact:
- Change PD → Regen PA → Regen SoW  (Full cascade)
- Change PA → Regen SoW only        (Partial cascade)
- Change SoW → No cascade           (Isolated change)
```

---

### PHASE 4: Approval & Export

**UI Component:** `render_approved_sow()`

**Actions:**
1. Lock all components (no more edits)
2. Generate JSON export:
   ```json
   {
     "customer_name": "ABC Company",
     "generated_at": "2025-11-04T14:30:00",
     "project_detail": { ... },
     "project_assumption": { ... },
     "scope_of_work": { 
       "tasks": [...],
       "total_man_days": 120.5,
       "total_tasks": 25
     },
     "judge_scores": {
       "project_detail": 85,
       "project_assumption": 78,
       "scope_of_work": 82
     },
     "version_history": [...]
   }
   ```
3. Download JSON file
4. Option to start new generation

---

## 🔍 Key Technical Details

### Content Formatting (Auto Line Breaks)

**Problem:** LLM generates task content as single long paragraph
```
"Conduct a kick-off meeting to finalize scope. This involves confirming templates. Deliverable: Scope document."
```

**Solution:** Auto-format in `engine.py` → `_parse_sow_response()`
```python
if '. ' in task_content:
    sentences = task_content.split('. ')
    formatted_content = '.\n\n'.join(sentences)
    # Result:
    # "Conduct a kick-off meeting to finalize scope.
    # 
    # This involves confirming templates.
    # 
    # Deliverable: Scope document."
```

**UI Rendering:** Streamlit's `st.markdown()` converts `\n\n` to paragraph breaks

### Judge Feedback Loop

**Without Previous Content (Bug Fixed):**
```python
# OLD (WRONG): LLM only sees feedback, not old content
context = f"Feedback: {feedback}\nRegenerate the component."
```

**With Previous Content (Current):**
```python
# NEW (CORRECT): LLM sees old content + feedback for comparison
context = f"""
Previous Project Detail:
{previous_detail.to_dict()}

Human Feedback:
{feedback}

Regenerate the Project Detail addressing the feedback while keeping other aspects.
"""
```

**Impact:** 
- LLM can now make targeted changes (not start from scratch)
- Better preservation of good content
- More accurate feedback incorporation

### Version Tracking

**Versioning Scheme:**
- `v_final_auto`: Auto-generated in PHASE 1 (passed judge)
- `v_human_1`: First human feedback regeneration
- `v_human_2`: Second human feedback regeneration
- `v_human_N`: Nth iteration

**ComponentVersion Storage:**
```python
@dataclass
class ComponentVersion:
    component: str  # "project_detail", "project_assumption", "scope_of_work"
    version: str
    content: Union[ProjectDetail, ProjectAssumption, ScopeOfWork]
    judge_result: JudgeResult
    created_at: datetime
    created_by: str  # "auto" or "human_feedback"
```

**History Lists:**
- `orchestrator.detail_history: List[ComponentVersion]`
- `orchestrator.assumption_history: List[ComponentVersion]`
- `orchestrator.sow_history: List[ComponentVersion]`

**Use Cases:**
- Rollback to previous version
- Compare versions side-by-side
- Audit trail of all changes
- Track judge score improvements over time

---

## 📊 Performance Metrics

**Typical Execution Times:**

**PHASE 1 (Auto-Generation):**
- Project Detail: 15-30 seconds (1 LLM call + 1 judge call)
- Project Assumption: 15-30 seconds (1 LLM call + 1 judge call)
- Scope of Work: 45-90 seconds (RAG query + 1 LLM call + 1 judge call)
- **Total:** 2-5 minutes (if all pass on first attempt)
- **With Retries:** Up to 10-15 minutes (if multiple components fail judge)

**PHASE 3 (Cascade Regeneration):**
- Regen PD only: ~30 seconds
- Regen PA only + cascade SoW: ~90 seconds
- Regen PD + cascade PA + SoW: ~3 minutes

**API Call Count (Successful Run):**
- PHASE 1: 6 calls (3 generation + 3 judge)
- Each PD regeneration: +2 calls (1 generation + 1 judge)
- Each PA regeneration with SoW cascade: +4 calls (2 generation + 2 judge)
- Each SoW regeneration: +2 calls (1 generation + 1 judge)

**BigQuery Queries:**
- 1 vector search per SoW generation
- Retrieves 20 similar tasks
- Query time: ~2-5 seconds

---

## ✅ Quality Assurance Checklist

**Before Deployment:**
- [ ] All 3 components generate successfully in PHASE 1
- [ ] Judge scores accurately reflect quality (spot check)
- [ ] Cascade logic works correctly (PD→PA→SoW, PA→SoW, SoW only)
- [ ] Previous content is passed to LLM during regeneration
- [ ] Task content has proper line breaks (readable format)
- [ ] RAG tasks are retrieved and adapted (not blindly copied)
- [ ] Version tracking works (history saved correctly)
- [ ] JSON export contains complete data
- [ ] UI displays all components correctly
- [ ] Error handling works (show user-friendly messages)

**Known Limitations:**
- RAG query may be slow with large task libraries (>10K tasks)
- LLM may occasionally generate invalid JSON (retry mechanism handles this)
- Judge scores can vary ±5 points between runs (LLM non-determinism)
- Very long SoW (>50 tasks) may hit token limits

---

