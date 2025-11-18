# SOW Generation - Phase 2

## Overview

Phase 2 của hệ thống tự động tạo **Project Details** và **Project Assumptions** dựa trên thông tin khách hàng và câu trả lời từ questionnaire (Phase 1).

## Features

### 1. Generate Project Detail
**Input:**
- Client Information (từ Phase 1)
- Questionnaire Answers (câu trả lời của client)

**Output:**
- **Overview**: Tổng quan dự án 2-3 đoạn văn
- **Objectives**: 4-8 mục tiêu SMART
- **Scope Summary**: Phạm vi dự án (in-scope và out-of-scope)
- **Key Features**: 5-10 tính năng chính
- **Deliverables**: Danh sách sản phẩm bàn giao

### 2. Generate Project Assumptions
**Input:**
- Client Information
- Questionnaire Answers
- Project Detail (đã tạo ở bước trước)

**Output:**
- **Technical Assumptions**: Giả định kỹ thuật
- **Business Assumptions**: Giả định nghiệp vụ
- **Resource Assumptions**: Giả định về nguồn lực
- **Timeline Assumptions**: Giả định về timeline
- **Risk Assumptions**: Giả định về rủi ro

### 3. Feedback Loop
Cả 2 features đều hỗ trợ **regeneration với feedback** tương tự Phase 1:
- User có thể nhập feedback
- Hệ thống sẽ cải thiện output dựa trên feedback
- Giữ nguyên context và thông tin gốc

## Architecture

```
app/scope_of_work/
├── model.py          # Data models (ClientInformation, ProjectDetail, ProjectAssumption)
├── engine.py         # SOWEngine - Logic generation
├── prompts.py        # System prompts và context builders
├── test.py           # Test script
└── sample_*.json     # Sample data files
```

## Technology Stack

- **LLM**: Google Gemini 2.0 Flash Exp
- **Framework**: Python + Pydantic
- **UI**: Streamlit (sow_phase2_ui.py)
- **Config**: JSON Schema with strict validation

## Usage

### Option 1: Run Web UI

```bash
cd app
streamlit run sow_phase2_ui.py
```

### Option 2: Run Test Script

```bash
cd app/scope_of_work
python test.py
```

### Option 3: Use Programmatically

```python
from scope_of_work.engine import SOWEngine
from scope_of_work.model import *

# Initialize engine
engine = SOWEngine(google_api_key="your-api-key")

# Create client info
client_info = ClientInformation(
    customer_name="ABC Company",
    business_domain="IT Services",
    requirements="Build CRM system",
    audience="Sales Team",
    language="English"
)

# Create questionnaire answers
answers = [
    QuestionnaireAnswer(
        question_id="q1",
        question_text="What are your objectives?",
        section="Background",
        answer="Improve sales productivity by 30%"
    )
]

# Generate project detail
input_data = ProjectDetailInput(
    client_info=client_info,
    questionnaire_answers=answers
)
project_detail = engine.generate_project_detail(input_data)

# Generate project assumptions
assumption_input = ProjectAssumptionInput(
    client_info=client_info,
    questionnaire_answers=answers,
    project_detail=project_detail
)
project_assumption = engine.generate_project_assumption(assumption_input)
```

## Data Models

### ClientInformation
```python
@dataclass
class ClientInformation:
    customer_name: str
    business_domain: str
    requirements: str
    audience: str
    language: str
    project_type: Optional[str]
    budget_range: Optional[str]
    timeline: Optional[str]
    additional_context: Optional[str]
```

### QuestionnaireAnswer
```python
@dataclass
class QuestionnaireAnswer:
    question_id: str
    question_text: str
    section: str
    answer: str
```

### ProjectDetail
```python
@dataclass
class ProjectDetail:
    detail_id: str
    customer_name: str
    business_domain: str
    overview: str
    objectives: List[str]
    scope_summary: str
    key_features: List[str]
    deliverables: List[str]
    created_at: datetime
    language: str
```

### ProjectAssumption
```python
@dataclass
class ProjectAssumption:
    assumption_id: str
    customer_name: str
    business_domain: str
    technical_assumptions: List[str]
    business_assumptions: List[str]
    resource_assumptions: List[str]
    timeline_assumptions: List[str]
    risk_assumptions: List[str]
    created_at: datetime
    language: str
```

## Configuration

### GenerationConfig
```python
@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_retries: int = 3
    language: str = "English"
```

## Sample Files

### sample_questionnaire_answers.json
File mẫu chứa 11 câu hỏi và câu trả lời để test. Có thể upload file này trong UI hoặc sử dụng trong test script.

## Prompts

### Project Detail Prompt
- **Role**: Senior Solution Architect tại Google Cloud Partner
- **Task**: Tạo comprehensive project details
- **Guidelines**: SMART objectives, clear scope, specific features & deliverables
- **Output**: JSON với 5 sections

### Project Assumption Prompt
- **Role**: Senior Solution Architect
- **Task**: Tạo comprehensive project assumptions
- **Guidelines**: Realistic, specific, categorized assumptions
- **Output**: JSON với 5 categories

## Error Handling

- **Retry Mechanism**: Tự động retry 3 lần khi LLM fail
- **Validation**: Pydantic validation cho tất cả inputs/outputs
- **Logging**: Chi tiết logs cho debugging
- **Graceful Degradation**: Clear error messages cho users

## Export Options

### JSON Export
- Export Project Detail
- Export Project Assumptions
- Export Complete SOW Package (tất cả cùng lúc)

### Format
```json
{
  "client_info": {...},
  "project_detail": {...},
  "project_assumptions": {...}
}
```

## Testing

Run test script:
```bash
cd app/scope_of_work
python test.py
```

Expected output:
- ✅ API Key validation
- ✅ Engine initialization
- ✅ Project detail generation with sample data
- ✅ Project assumptions generation
- 💾 JSON files saved: `sample_project_detail_output.json`, `sample_project_assumption_output.json`

## Integration với Phase 1

Phase 2 sử dụng output từ Phase 1:
1. **Client Information**: Từ form input Phase 1
2. **Questionnaire**: Từ generated questionnaire Phase 1
3. **Answers**: Client điền vào questionnaire

Flow hoàn chỉnh:
```
Phase 1: Input → Generate Questionnaire → Send to Client
         ↓
Client fills questionnaire
         ↓
Phase 2: Client Info + Answers → Generate Project Detail
         ↓
Project Detail → Generate Project Assumptions
         ↓
Complete SOW Package
```

## Future Enhancements

- [ ] RAG for similar project details/assumptions
- [ ] Template management
- [ ] Multi-language support improvement
- [ ] PDF export
- [ ] Google Docs integration
- [ ] Version control
- [ ] Collaborative editing

## Requirements

```
google-generativeai>=0.3.0
pydantic>=2.0.0
python-dotenv>=1.0.0
streamlit>=1.28.0
```

## Environment Variables

```bash
GOOGLE_API_KEY=your-gemini-api-key
```

## Notes

- Temperature = 0.7 cân bằng giữa creativity và consistency
- Language support: English, Vietnamese (có thể mở rộng)
- Max retries = 3 để đảm bảo reliability
- JSON Schema validation đảm bảo output format đúng

## Support

Nếu gặp lỗi:
1. Check API key trong .env
2. Check logs trong console
3. Xem sample files để hiểu format
4. Run test.py để validate setup
