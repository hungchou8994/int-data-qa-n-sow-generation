# Observability & Monitoring Setup

## 🔍 Current State

Your project **CAN** implement full observability! Here's the comprehensive setup:

---

## 1. 📊 Cloud Logging (Logs)

### Already Implemented (Basic)
```python
# Your current code
import logging
logger = logging.getLogger(__name__)
logger.info("Processing questionnaire...")
```

### Enhanced Setup for Cloud Run

**Add structured logging:**
```python
# app/utils/logging_config.py
import logging
import json
from datetime import datetime
from google.cloud import logging as cloud_logging

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        
        # Cloud Logging client
        try:
            client = cloud_logging.Client()
            client.setup_logging()
        except:
            # Local development fallback
            logging.basicConfig(level=logging.INFO)
    
    def log_event(self, event_type, data, severity="INFO"):
        """Log structured data to Cloud Logging"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "data": data
        }
        
        if severity == "INFO":
            self.logger.info(json.dumps(log_entry))
        elif severity == "WARNING":
            self.logger.warning(json.dumps(log_entry))
        elif severity == "ERROR":
            self.logger.error(json.dumps(log_entry))
    
    def log_generation(self, customer, total_questions, judge_score, duration_ms):
        """Log questionnaire generation event"""
        self.log_event("questionnaire_generation", {
            "customer_name": customer,
            "total_questions": total_questions,
            "judge_score": judge_score,
            "duration_ms": duration_ms
        })
    
    def log_export(self, customer, worksheet_name, success):
        """Log sheet export event"""
        self.log_event("sheet_export", {
            "customer_name": customer,
            "worksheet_name": worksheet_name,
            "success": success
        })
```

**Usage in your code:**
```python
# In questionnaire_ui.py
from utils.logging_config import StructuredLogger
logger = StructuredLogger(__name__)

# Log generation
start = time.time()
questionnaire = generate_questionnaire(...)
duration = (time.time() - start) * 1000

logger.log_generation(
    customer=questionnaire.customer_name,
    total_questions=questionnaire.total_questions,
    judge_score=judge_result['score'],
    duration_ms=duration
)
```

---

## 2. 📈 Cloud Monitoring (Metrics)

### Custom Metrics with OpenTelemetry

**Install dependencies:**
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-gcp-monitoring
```

**Setup metrics:**
```python
# app/utils/metrics.py
from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

def setup_metrics():
    """Initialize OpenTelemetry metrics"""
    exporter = CloudMonitoringMetricsExporter()
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    
    return metrics.get_meter(__name__)

# Create meter
meter = setup_metrics()

# Define metrics
generation_counter = meter.create_counter(
    "questionnaire_generations_total",
    description="Total number of questionnaire generations"
)

judge_score_histogram = meter.create_histogram(
    "judge_score",
    description="Distribution of judge scores"
)

export_success_counter = meter.create_counter(
    "sheet_exports_success",
    description="Successful sheet exports"
)

export_failure_counter = meter.create_counter(
    "sheet_exports_failure",
    description="Failed sheet exports"
)

rag_latency_histogram = meter.create_histogram(
    "rag_query_duration_ms",
    description="RAG query latency in milliseconds"
)
```

**Usage:**
```python
# Increment counters
generation_counter.add(1, {"customer": customer_name, "domain": business_domain})

# Record judge score
judge_score_histogram.record(judge_result['score'], {"status": judge_result['status']})

# Record export
if export_success:
    export_success_counter.add(1)
else:
    export_failure_counter.add(1)

# Record RAG latency
rag_latency_histogram.record(duration_ms, {"query_type": "vector_search"})
```

---

## 3. 🔎 Cloud Trace (Distributed Tracing)

### Trace generation workflow end-to-end

**Setup OpenTelemetry Tracing:**
```python
# app/utils/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def setup_tracing():
    """Initialize OpenTelemetry tracing"""
    exporter = CloudTraceSpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)
    
    # Auto-instrument HTTP requests
    RequestsInstrumentor().instrument()
    
    return trace.get_tracer(__name__)

tracer = setup_tracing()
```

**Instrument your workflow:**
```python
# In orchestrator.py
from utils.tracing import tracer

def generate_with_validation(self, input_data, config):
    with tracer.start_as_current_span("questionnaire_generation") as span:
        span.set_attribute("customer.name", input_data.customer_name)
        span.set_attribute("domain", input_data.business_domain)
        
        # RAG retrieval
        with tracer.start_as_current_span("rag_retrieval"):
            rag_questions = self.retriever.search(...)
        
        # LLM generation
        with tracer.start_as_current_span("llm_generation"):
            questionnaire = self.engine.generate(...)
        
        # Judge evaluation
        with tracer.start_as_current_span("judge_evaluation") as judge_span:
            judge_result = self.judge.evaluate(...)
            judge_span.set_attribute("score", judge_result['score'])
            judge_span.set_attribute("status", judge_result['status'])
        
        return result
```

---

## 4. 🚨 Cloud Error Reporting

**Automatic error tracking:**
```python
# app/utils/error_reporting.py
from google.cloud import error_reporting

error_client = error_reporting.Client()

def report_error(error, context=None):
    """Report error to Cloud Error Reporting"""
    try:
        error_client.report_exception(
            http_context=context
        )
    except Exception as e:
        print(f"Failed to report error: {e}")
```

**Usage in exception handling:**
```python
try:
    questionnaire = generate_questionnaire(...)
except Exception as e:
    report_error(e, context={
        "user": "streamlit_user",
        "url": "/questionnaire",
        "method": "POST"
    })
    st.error(f"Error: {str(e)}")
```

---

## 5. 📊 Custom Dashboards

### Cloud Monitoring Dashboard (JSON config)

```json
{
  "displayName": "Questionnaire Generator Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Questionnaire Generations (Last 24h)",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/questionnaire_generations_total\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Judge Score Distribution",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/judge_score\"",
                  "aggregation": {
                    "alignmentPeriod": "300s",
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Export Success Rate",
          "scorecard": {
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "metric.type=\"custom.googleapis.com/sheet_exports_success\"",
                "aggregation": {
                  "alignmentPeriod": "3600s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "RAG Query Latency (p95)",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/rag_query_duration_ms\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_DELTA",
                    "crossSeriesReducer": "REDUCE_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
```

---

## 6. 🔔 Alerting

### Create Alerts in Cloud Monitoring

**Alert 1: High Error Rate**
```yaml
displayName: "High Error Rate - Questionnaire Generation"
conditions:
  - displayName: "Error rate > 10%"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class="5xx"'
      comparison: COMPARISON_GT
      thresholdValue: 0.1
      duration: 300s
notificationChannels:
  - projects/int-data-qa-n-sow-generation/notificationChannels/YOUR_CHANNEL_ID
```

**Alert 2: Low Judge Scores**
```yaml
displayName: "Low Judge Scores - Quality Issue"
conditions:
  - displayName: "Average judge score < 60"
    conditionThreshold:
      filter: 'metric.type="custom.googleapis.com/judge_score"'
      comparison: COMPARISON_LT
      thresholdValue: 60
      duration: 600s
      aggregations:
        - alignmentPeriod: 300s
          perSeriesAligner: ALIGN_MEAN
```

**Alert 3: High Latency**
```yaml
displayName: "High RAG Latency"
conditions:
  - displayName: "P95 latency > 5000ms"
    conditionThreshold:
      filter: 'metric.type="custom.googleapis.com/rag_query_duration_ms"'
      comparison: COMPARISON_GT
      thresholdValue: 5000
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          crossSeriesReducer: REDUCE_PERCENTILE_95
```

---

## 7. 📱 Notification Channels

### Setup Email/Slack notifications

**Create notification channel:**
```bash
# Email
gcloud alpha monitoring channels create \
  --display-name="Team Email" \
  --type=email \
  --channel-labels=email_address=team@cloudace.com

# Slack
gcloud alpha monitoring channels create \
  --display-name="Slack #alerts" \
  --type=slack \
  --channel-labels=url=YOUR_WEBHOOK_URL
```

---

## 8. 🔧 Implementation Checklist

### Phase 1: Basic Observability (1-2 days)
- [ ] Add structured logging to all major functions
- [ ] Implement basic metrics (generations, exports)
- [ ] Setup error reporting
- [ ] Create basic dashboard

### Phase 2: Advanced Monitoring (2-3 days)
- [ ] Add distributed tracing
- [ ] Implement custom metrics for judge scores
- [ ] Add RAG latency tracking
- [ ] Create comprehensive dashboard

### Phase 3: Alerting (1 day)
- [ ] Setup notification channels
- [ ] Create error rate alerts
- [ ] Create performance alerts
- [ ] Test alert delivery

### Phase 4: Optimization (ongoing)
- [ ] Review logs and metrics
- [ ] Optimize slow queries
- [ ] Improve error handling
- [ ] Fine-tune alerts

---

## 9. 📊 Sample Queries

### Useful Log Queries

**Find failed generations:**
```sql
resource.type="cloud_run_revision"
jsonPayload.event_type="questionnaire_generation"
jsonPayload.data.judge_score < 75
```

**Export failures:**
```sql
resource.type="cloud_run_revision"
jsonPayload.event_type="sheet_export"
jsonPayload.data.success=false
```

**Slow RAG queries:**
```sql
resource.type="cloud_run_revision"
jsonPayload.rag_duration_ms > 3000
```

---

## 10. 💰 Cost Estimation

**Observability costs (estimated monthly):**
- Cloud Logging: ~$0.50/GB (first 50GB free)
- Cloud Monitoring: Free tier covers most usage
- Cloud Trace: ~$0.20/million spans
- Error Reporting: Free

**Estimated for 1000 requests/day:**
- Logs: ~2GB/month = **$1-2/month**
- Metrics: Within free tier = **$0**
- Traces: ~30K spans = **$0.01/month**
- **Total: ~$1-2/month**

---

## Quick Start

### 1. Update requirements.txt
```txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-gcp-monitoring>=1.5.0
opentelemetry-exporter-cloud-trace>=1.5.0
opentelemetry-instrumentation-requests>=0.41b0
google-cloud-logging>=3.8.0
google-cloud-error-reporting>=1.9.0
```

### 2. Add to Dockerfile
```dockerfile
# Already done - OpenTelemetry auto-configured for Cloud Run
```

### 3. Deploy with observability
```bash
gcloud run deploy questionnaire-generator \
  --set-env-vars="ENABLE_OBSERVABILITY=true"
```

### 4. View in Cloud Console
- Logs: https://console.cloud.google.com/logs
- Metrics: https://console.cloud.google.com/monitoring
- Traces: https://console.cloud.google.com/traces
- Errors: https://console.cloud.google.com/errors

---

## Summary

✅ **Your project CAN have full observability:**
- Structured logging for debugging
- Custom metrics for performance
- Distributed tracing for latency analysis
- Error reporting for quick fixes
- Dashboards for visualization
- Alerts for proactive monitoring

**Effort:** 4-6 days to implement fully
**ROI:** High - better debugging, performance insights, proactive alerts
