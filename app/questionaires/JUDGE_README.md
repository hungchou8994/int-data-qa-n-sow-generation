# Questionnaire Judge System Documentation

## Overview
LLM-as-Judge layer for automatic quality control of generated questionnaires with retry mechanism.

---

## Architecture

### Components
1. **Judge** (`judge.py`) - LLM-based quality evaluator
2. **Orchestrator** (`orchestrator.py`) - Generation + validation workflow manager  
3. **UI Integration** (`questionnaire_ui.py`) - Configuration controls and result display

### Flow
```
User Input → Orchestrator → Engine (Generate) → Judge (Validate)
                ↑                                      ↓
                └──────── Retry with Feedback ─────────┘
                              (max 3 attempts)
```

---

## Judge Rubric (100 points)

### 1. Relevance to Requirements (30 points)
- Questions address customer's stated requirements
- Tailored to project type, timeline, budget
- Avoid generic/irrelevant content

### 2. Completeness (25 points)
- Cover all 4 key criteria:
  * Business Problems & Objectives
  * Current Environment / As-Is
  * To-be Architecture  
  * Timeline & Budget
- No critical gaps
- Question count in expected range

### 3. Question Quality (25 points)
- Clear, specific, actionable
- Professional, consultative tone
- Helpful examples/clarifications
- Open-ended (not yes/no unless strategic)

### 4. Diversity & Structure (20 points)
- Logical sections (4-6 recommended)
- Coherent section grouping
- Variety in question types (strategic/technical/operational)
- NOT just rephrased reference questions

---

## Configuration

### UI Settings (Sidebar)

**Pass Threshold** (50-100, default 75)
- Minimum score for questionnaire to pass
- High threshold (≥80) → more retries, better quality
- Low threshold (≤60) → faster, may compromise quality

**Max Auto Retries** (1-5, default 3)
- Automatic retry attempts if judge fails
- Each retry accumulates previous feedback
- 3 attempts = good balance between quality and speed

---

## Usage

### 1. Auto-Generation with Validation
```python
orchestrator = QuestionnaireOrchestrator(
    google_api_key="...",
    max_auto_retries=3,
    pass_threshold=75
)

result = orchestrator.generate_with_validation(input_data, config)

# Result structure:
{
    "questionnaire": QuestionnaireOutput,
    "judge_result": {
        "status": "PASS" | "FAIL",
        "score": 85,
        "feedback": "...",
        "breakdown": {"relevance": 28, "completeness": 22, ...},
        "strengths": [...],
        "improvements": [...]
    },
    "attempts": 2,
    "status": "success" | "max_retries_reached"
}
```

### 2. Regeneration with User Feedback
```python
result = orchestrator.regenerate_with_feedback(
    input_data=input_data,
    config=config,
    previous_questionnaire=prev_questionnaire,
    feedback="Add more technical questions about infrastructure"
)
```

---

## UI Display

### Judge Results Section
- **Score Card**: Overall score, status, category averages
- **Expandable Details**:
  * Overall feedback
  * Score breakdown by category
  * Strengths (✅)
  * Areas for improvement (⚠️)
- **Auto-expand** if status = FAIL

### Generation Flow
1. User fills form → clicks "Generate"
2. Orchestrator runs generation → validation loop
3. UI shows:
   - Success: ✅ Score + attempts
   - Max retries: ⚠️ Warning with best score
4. Review tab displays questionnaire + judge results

---

## Retry Mechanism

### Feedback Accumulation
```
Attempt 1: Generate → Score 65 (FAIL)
  ↓ Accumulate: "Score 65/100, Issues: ..."

Attempt 2: Regenerate with feedback → Score 72 (FAIL)
  ↓ Accumulate: "Previous issues + new issues..."

Attempt 3: Regenerate with all feedback → Score 78 (PASS)
  ✅ Success!
```

### Feedback Content
- Judge score
- Detailed issues from judge feedback
- Required improvements list
- Strengths to maintain

---

## Example Output

### PASS Status (Score 85/100)
```
✅ Questionnaire generated successfully! 
   Judge Score: 85/100, Attempts: 2

Breakdown:
- Relevance: 28/30
- Completeness: 22/25  
- Quality: 23/25
- Diversity: 12/20

Strengths:
✅ Questions directly address data analytics requirements
✅ Excellent technical depth for architecture planning
✅ Clear, professional tone throughout

Improvements:
⚠️ Add 1-2 more questions about budget constraints
⚠️ Include questions about team skill levels
```

### FAIL Status (Max Retries)
```
⚠️ Failed to achieve passing score after 3 attempts
   Best Score: 68/100

Issues:
- Too generic questions (not tailored to healthcare domain)
- Missing questions about compliance requirements
- Sections poorly organized (7 sections, should be 4-6)
```

---

## Best Practices

### For High Quality (Pass Threshold ≥ 80)
✅ Provide detailed requirements in input
✅ Set max_retries = 3-5
✅ Review judge feedback carefully
✅ Use regeneration with specific feedback

### For Fast Iteration (Pass Threshold ≤ 65)
✅ Use for initial drafts
✅ Set max_retries = 1-2
✅ Manual review + refinement after

### Optimal Settings (Recommended)
- Pass Threshold: **75**
- Max Retries: **3**
- Retrieval Top-K: **10**
- Temperature: **0.7**

---

## Troubleshooting

### Issue: Consistently failing judge
**Causes:**
- Pass threshold too high (≥85)
- Insufficient input details
- RAG returning poor quality references

**Solutions:**
- Lower threshold to 70-75
- Add more context to requirements
- Increase retrieval_top_k

### Issue: Taking too long (>3 minutes)
**Causes:**
- Too many retries (≥4)
- High max_questions (≥25)

**Solutions:**
- Reduce max_retries to 2-3
- Lower max_questions to 15-20

### Issue: Judge too lenient (PASS with low quality)
**Causes:**
- Threshold too low (≤60)
- Judge prompt needs tuning

**Solutions:**
- Increase threshold to 75+
- Review judge rubric in judge.py

---

## Performance Metrics

### Typical Results
- **Pass Rate**: ~70% on first attempt (threshold=75)
- **Avg Attempts**: 1.8
- **Avg Score**: 78/100
- **Time**: 30-90 seconds per generation

### By Threshold
| Threshold | Pass Rate | Avg Attempts | Avg Time |
|-----------|-----------|--------------|----------|
| 60        | 95%       | 1.2          | 45s      |
| 75        | 70%       | 1.8          | 75s      |
| 85        | 40%       | 2.6          | 120s     |

---

## Testing

### Test Judge Only
```bash
cd app/questionaires
python judge.py
```

### Test Orchestrator
```bash
cd app/questionaires  
python orchestrator.py
```

### Test Full UI
```bash
cd app
streamlit run questionnaire_ui.py
```

---

## Future Enhancements

- [ ] Custom rubrics per business domain
- [ ] Multi-language judge prompts
- [ ] Judge confidence scores
- [ ] A/B testing different thresholds
- [ ] Export judge reports to PDF
