# Phase 1 Execution Plan: Foundation Monitoring

## Overview

This document outlines the detailed implementation plan for Phase 1 of the Memo Bot observability system. Phase 1 focuses on establishing basic monitoring and alerting using GCP's native tools, without the complexity of distributed tracing.

## Phase 1 Goals

- **Basic monitoring** for all endpoints
- **OpenAI cost and performance tracking**
- **Rate limiting effectiveness monitoring**
- **Error rate monitoring and alerting**
- **Structured logging implementation**

## Implementation Steps

### Step 1: Deploy to Cloud Run (if not already)

#### Prerequisites
- Ensure application is ready for Cloud Run deployment
- Verify environment variables are configured
- Test local functionality

#### Deployment Commands
```bash
# Build and deploy to Cloud Run
gcloud run deploy memo-bot-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="OPENAI_API_KEY=$OPENAI_API_KEY,OPENAI_MODEL=gpt-5-nano"
```

#### Verification
- [ ] Application deploys successfully
- [ ] Health endpoint responds
- [ ] All endpoints function correctly
- [ ] Environment variables are set

### Step 2: Enable Cloud Monitoring Built-in Metrics

#### Automatic Metrics Available
Once deployed to Cloud Run, the following metrics are automatically available:

- **Request Count**: `run.googleapis.com/request_count`
- **Request Latency**: `run.googleapis.com/request_latencies`
- **Memory Usage**: `run.googleapis.com/memory_utilization`
- **CPU Usage**: `run.googleapis.com/cpu_utilization`
- **Instance Count**: `run.googleapis.com/instance_count`

#### Verification
- [ ] Cloud Monitoring console shows metrics
- [ ] Basic dashboard displays request data
- [ ] Metrics are updating in real-time

### Step 3: Implement Custom Metrics for OpenAI Calls

#### 3.1 Add Cloud Monitoring Dependencies

Update `requirements.txt`:
```txt
# Add to existing requirements.txt
google-cloud-monitoring==1.11.0
```

#### 3.2 Create Monitoring Module

Create `backend/monitoring.py`:
```python
"""
Monitoring module for custom metrics and logging.
"""
import os
import time
import logging
from typing import Dict, Any, Optional
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import MetricDescriptor, TimeSeries, Point
from google.protobuf.timestamp_pb2 import Timestamp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoBotMetrics:
    """Custom metrics for Memo Bot application."""
    
    def __init__(self):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0574433212")
        self.project_name = f"projects/{self.project_id}"
        
    def create_custom_metric(self, metric_type: str, description: str) -> None:
        """Create a custom metric descriptor."""
        try:
            descriptor = MetricDescriptor(
                type=f"custom.googleapis.com/memo_bot/{metric_type}",
                description=description,
                metric_kind=monitoring_v3.MetricDescriptor.MetricKind.GAUGE,
                value_type=monitoring_v3.MetricDescriptor.ValueType.DOUBLE,
                labels=[
                    monitoring_v3.LabelDescriptor(key="user_id", description="User ID"),
                    monitoring_v3.LabelDescriptor(key="endpoint", description="API endpoint"),
                    monitoring_v3.LabelDescriptor(key="model", description="OpenAI model used"),
                ]
            )
            
            self.client.create_metric_descriptor(
                name=self.project_name,
                metric_descriptor=descriptor
            )
            logger.info(f"Created metric: {metric_type}")
        except Exception as e:
            logger.warning(f"Metric {metric_type} may already exist: {e}")
    
    def record_openai_metrics(self, 
                           user_id: str, 
                           endpoint: str, 
                           model: str,
                           input_tokens: int,
                           output_tokens: int,
                           latency_ms: float,
                           cost_usd: float,
                           success: bool) -> None:
        """Record OpenAI API metrics."""
        try:
            # Create time series for each metric
            timestamp = Timestamp()
            timestamp.FromDatetime(time.datetime.utcnow())
            
            metrics = [
                ("openai_input_tokens", input_tokens, "Input tokens used"),
                ("openai_output_tokens", output_tokens, "Output tokens generated"),
                ("openai_latency_ms", latency_ms, "API response time in milliseconds"),
                ("openai_cost_usd", cost_usd, "Estimated cost in USD"),
                ("openai_success_rate", 1.0 if success else 0.0, "API call success indicator"),
            ]
            
            for metric_name, value, description in metrics:
                self.create_custom_metric(metric_name, description)
                
                series = TimeSeries(
                    metric={
                        "type": f"custom.googleapis.com/memo_bot/{metric_name}",
                        "labels": {
                            "user_id": user_id,
                            "endpoint": endpoint,
                            "model": model,
                        }
                    },
                    resource={
                        "type": "cloud_run_revision",
                        "labels": {
                            "project_id": self.project_id,
                            "service_name": "memo-bot-backend",
                        }
                    },
                    points=[Point({"value": {"double_value": value}, "interval": {"end_time": timestamp}})]
                )
                
                self.client.create_time_series(name=self.project_name, time_series=[series])
                
        except Exception as e:
            logger.error(f"Failed to record OpenAI metrics: {e}")
    
    def record_rate_limit_metrics(self,
                                user_id: str,
                                endpoint: str,
                                rate_limit_hit: bool,
                                remaining_quota: int) -> None:
        """Record rate limiting metrics."""
        try:
            timestamp = Timestamp()
            timestamp.FromDatetime(time.datetime.utcnow())
            
            # Rate limit hit metric
            self.create_custom_metric("rate_limit_hit", "Rate limit hit indicator")
            series = TimeSeries(
                metric={
                    "type": "custom.googleapis.com/memo_bot/rate_limit_hit",
                    "labels": {
                        "user_id": user_id,
                        "endpoint": endpoint,
                    }
                },
                resource={
                    "type": "cloud_run_revision",
                    "labels": {
                        "project_id": self.project_id,
                        "service_name": "memo-bot-backend",
                    }
                },
                points=[Point({"value": {"double_value": 1.0 if rate_limit_hit else 0.0}, "interval": {"end_time": timestamp}})]
            )
            
            self.client.create_time_series(name=self.project_name, time_series=[series])
            
            # Remaining quota metric
            self.create_custom_metric("rate_limit_remaining", "Remaining rate limit quota")
            series = TimeSeries(
                metric={
                    "type": "custom.googleapis.com/memo_bot/rate_limit_remaining",
                    "labels": {
                        "user_id": user_id,
                        "endpoint": endpoint,
                    }
                },
                resource={
                    "type": "cloud_run_revision",
                    "labels": {
                        "project_id": self.project_id,
                        "service_name": "memo-bot-backend",
                    }
                },
                points=[Point({"value": {"double_value": float(remaining_quota)}, "interval": {"end_time": timestamp}})]
            )
            
            self.client.create_time_series(name=self.project_name, time_series=[series])
            
        except Exception as e:
            logger.error(f"Failed to record rate limit metrics: {e}")

# Global metrics instance
metrics = MemoBotMetrics()
```

#### 3.3 Integrate Metrics into Main Application

Update `backend/main.py` to include monitoring:

```python
# Add to imports
from monitoring import metrics
import time

# Update chat endpoint to include metrics
@app.post("/api/chat")
@apply_rate_limit("/api/chat")
async def chat(request: Request, payload: Dict[str, Any], uid: str = Depends(get_verified_uid)):
    start_time = time.time()
    msg = (payload or {}).get("message", "")
    if not isinstance(msg, str) or not msg.strip():
        raise HTTPException(400, "message is required")

    # Persist user message
    log_message(uid, "user", msg)

    # Assemble context
    facts = get_top_facts(uid, limit=6)
    system_prompt = _build_system_prompt(facts)
    history = get_last_messages(uid, limit=6)

    if not _use_openai:
        # Record metrics for fake response
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_openai_metrics(
            user_id=uid,
            endpoint="/api/chat",
            model="none",
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            cost_usd=0.0,
            success=True
        )
        
        async def fake_stream():
            for piece in ["(no OpenAI key) ", "You said: ", msg]:
                yield f"data:{json.dumps(piece)}\n\n"
                await asyncio.sleep(0.02)
            yield "data:[DONE]\n\n"
        return StreamingResponse(fake_stream(), media_type="text/event-stream")

    def to_messages():
        msgs = [{"role": "system", "content": system_prompt}]
        for h in history:
            msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": msg})
        return msgs

    # Calculate input tokens (rough estimation)
    input_tokens = sum(len(msg["content"].split()) for msg in to_messages()) * 1.3  # Rough token estimation
    
    try:
        stream = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=to_messages(),
            stream=True,
        )
        
        async def sse():
            full = []
            output_tokens = 0
            for event in stream:
                delta = (event.choices[0].delta or {})
                token = getattr(delta, "content", None) if hasattr(delta, "content") else delta.get("content")
                if token:
                    full.append(token)
                    output_tokens += len(token.split()) * 1.3  # Rough token estimation
                    yield f"data:{json.dumps(token)}\n\n"
            
            assistant_text = "".join(full)
            log_message(uid, "assistant", assistant_text)
            
            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            cost_usd = _estimate_cost(input_tokens, output_tokens, OPENAI_MODEL)
            
            metrics.record_openai_metrics(
                user_id=uid,
                endpoint="/api/chat",
                model=OPENAI_MODEL,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                success=True
            )
            
            yield "data:[DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")
        
    except Exception as e:
        # Record error metrics
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_openai_metrics(
            user_id=uid,
            endpoint="/api/chat",
            model=OPENAI_MODEL,
            input_tokens=int(input_tokens),
            output_tokens=0,
            latency_ms=latency_ms,
            cost_usd=0.0,
            success=False
        )
        
        logger.error(f"OpenAI API Error: {e}")
        raise HTTPException(500, f"OpenAI API call failed: {e}")

def _estimate_cost(input_tokens: float, output_tokens: float, model: str) -> float:
    """Estimate cost based on token usage and model."""
    # Rough cost estimates (update with actual pricing)
    model_costs = {
        "gpt-5-nano": {"input": 0.0000015, "output": 0.000006},  # $0.0015/1K input, $0.006/1K output
        "gpt-4": {"input": 0.00003, "output": 0.00006},  # $0.03/1K input, $0.06/1K output
        "gpt-3.5-turbo": {"input": 0.0000015, "output": 0.000002},  # $0.0015/1K input, $0.002/1K output
    }
    
    costs = model_costs.get(model, model_costs["gpt-5-nano"])
    return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])
```

#### 3.4 Update Rate Limiter with Metrics

Update `backend/rate_limiter.py`:

```python
# Add to imports
from monitoring import metrics

# Update rate_limit_exceeded_handler
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    # Extract retry_after from the exception if available
    retry_after = getattr(exc, 'retry_after', None)
    
    # Record rate limit metrics
    uid = getattr(request.state, 'uid', 'unknown')
    endpoint = request.url.path
    
    # Get remaining quota (this would need to be implemented based on your rate limiter)
    remaining_quota = 0  # Placeholder
    
    metrics.record_rate_limit_metrics(
        user_id=uid,
        endpoint=endpoint,
        rate_limit_hit=True,
        remaining_quota=remaining_quota
    )
    
    response = JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": retry_after,
            "endpoint": endpoint,
            "uid": uid
        }
    )
    
    # Add retry-after header if available
    if retry_after:
        response.headers["Retry-After"] = str(retry_after)
    return response
```

### Step 4: Set Up Basic Alerting

#### 4.1 Create Alert Policies

Create `backend/alert_policies.yaml`:

```yaml
# Alert Policies for Memo Bot
policies:
  - displayName: "OpenAI API Error Rate High"
    conditions:
      - displayName: "OpenAI API Error Rate > 5%"
        conditionThreshold:
          filter: 'metric.type="custom.googleapis.com/memo_bot/openai_success_rate"'
          comparison: COMPARISON_LESS_THAN
          thresholdValue: 0.95
          duration: 300s  # 5 minutes
    alertStrategy:
      autoClose: 3600s  # Auto-close after 1 hour
    notificationChannels:
      - projects/PROJECT_ID/notificationChannels/CHANNEL_ID

  - displayName: "High Response Time"
    conditions:
      - displayName: "P95 Response Time > 2s"
        conditionThreshold:
          filter: 'metric.type="run.googleapis.com/request_latencies"'
          comparison: COMPARISON_GREATER_THAN
          thresholdValue: 2000  # 2 seconds in milliseconds
          duration: 300s
    alertStrategy:
      autoClose: 3600s
    notificationChannels:
      - projects/PROJECT_ID/notificationChannels/CHANNEL_ID

  - displayName: "High Rate Limit Hits"
    conditions:
      - displayName: "Rate Limit Hits > 20%"
        conditionThreshold:
          filter: 'metric.type="custom.googleapis.com/memo_bot/rate_limit_hit"'
          comparison: COMPARISON_GREATER_THAN
          thresholdValue: 0.2
          duration: 300s
    alertStrategy:
      autoClose: 3600s
    notificationChannels:
      - projects/PROJECT_ID/notificationChannels/CHANNEL_ID

  - displayName: "High OpenAI Cost"
    conditions:
      - displayName: "Daily OpenAI Cost > $50"
        conditionThreshold:
          filter: 'metric.type="custom.googleapis.com/memo_bot/openai_cost_usd"'
          comparison: COMPARISON_GREATER_THAN
          thresholdValue: 50.0
          duration: 86400s  # 24 hours
    alertStrategy:
      autoClose: 86400s
    notificationChannels:
      - projects/PROJECT_ID/notificationChannels/CHANNEL_ID
```

#### 4.2 Create Notification Channels

```bash
# Create email notification channel
gcloud alpha monitoring channels create \
  --display-name="Memo Bot Alerts" \
  --type="email" \
  --channel-labels="email_address=your-email@example.com"

# Create Slack notification channel (if using Slack)
gcloud alpha monitoring channels create \
  --display-name="Memo Bot Slack Alerts" \
  --type="slack" \
  --channel-labels="slack_channel=#alerts"
```

### Step 5: Configure Structured Logging

#### 5.1 Update Logging Configuration

Create `backend/logging_config.py`:

```python
"""
Structured logging configuration for Memo Bot.
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'openai_model'):
            log_entry['openai_model'] = record.openai_model
        if hasattr(record, 'input_tokens'):
            log_entry['input_tokens'] = record.input_tokens
        if hasattr(record, 'output_tokens'):
            log_entry['output_tokens'] = record.output_tokens
        if hasattr(record, 'latency_ms'):
            log_entry['latency_ms'] = record.latency_ms
        if hasattr(record, 'cost_usd'):
            log_entry['cost_usd'] = record.cost_usd
        if hasattr(record, 'rate_limit_key'):
            log_entry['rate_limit_key'] = record.rate_limit_key
        if hasattr(record, 'rate_limit_hit'):
            log_entry['rate_limit_hit'] = record.rate_limit_hit
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging() -> None:
    """Setup structured logging."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(StructuredFormatter())
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger("google.cloud").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def log_request(level: str, message: str, **kwargs: Any) -> None:
    """Log request with structured data."""
    logger = logging.getLogger("memo_bot.request")
    record = logger.makeRecord(
        "memo_bot.request", 
        getattr(logging, level.upper()), 
        "", 0, message, (), None
    )
    
    # Add extra fields
    for key, value in kwargs.items():
        setattr(record, key, value)
    
    logger.handle(record)
```

#### 5.2 Integrate Logging into Application

Update `backend/main.py`:

```python
# Add to imports
from logging_config import setup_logging, log_request
import uuid

# Setup logging at startup
setup_logging()

# Update chat endpoint with structured logging
@app.post("/api/chat")
@apply_rate_limit("/api/chat")
async def chat(request: Request, payload: Dict[str, Any], uid: str = Depends(get_verified_uid)):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    log_request("info", "Chat request started", 
               user_id=uid, 
               endpoint="/api/chat", 
               request_id=request_id)
    
    # ... existing code ...
    
    try:
        # ... OpenAI API call ...
        
        # Log successful completion
        latency_ms = (time.time() - start_time) * 1000
        log_request("info", "Chat request completed successfully",
                   user_id=uid,
                   endpoint="/api/chat",
                   request_id=request_id,
                   openai_model=OPENAI_MODEL,
                   input_tokens=int(input_tokens),
                   output_tokens=int(output_tokens),
                   latency_ms=latency_ms,
                   cost_usd=cost_usd)
        
    except Exception as e:
        # Log error
        latency_ms = (time.time() - start_time) * 1000
        log_request("error", f"Chat request failed: {e}",
                   user_id=uid,
                   endpoint="/api/chat",
                   request_id=request_id,
                   openai_model=OPENAI_MODEL,
                   input_tokens=int(input_tokens),
                   latency_ms=latency_ms)
        raise
```

## Verification Checklist

### Deployment Verification
- [ ] Application deploys to Cloud Run successfully
- [ ] Health endpoint responds correctly
- [ ] All API endpoints function as expected
- [ ] Environment variables are properly set

### Monitoring Verification
- [ ] Cloud Monitoring shows built-in metrics
- [ ] Custom metrics are being recorded
- [ ] Metrics appear in Cloud Monitoring console
- [ ] Metrics update in real-time

### Alerting Verification
- [ ] Alert policies are created
- [ ] Notification channels are configured
- [ ] Test alerts can be triggered
- [ ] Alert notifications are received

### Logging Verification
- [ ] Structured logs are generated
- [ ] Logs appear in Cloud Logging
- [ ] Log-based metrics can be created
- [ ] Log queries work correctly

## Testing Plan

### Unit Tests
- [ ] Test metrics recording functions
- [ ] Test logging configuration
- [ ] Test cost estimation function
- [ ] Test rate limit metrics

### Integration Tests
- [ ] Test full request flow with metrics
- [ ] Test error scenarios with metrics
- [ ] Test rate limiting with metrics
- [ ] Test logging integration

### Load Tests
- [ ] Test metrics under load
- [ ] Verify no performance impact
- [ ] Test alerting under load
- [ ] Verify log volume

## Rollback Plan

If issues arise during implementation:

1. **Disable custom metrics** by commenting out metrics calls
2. **Revert to basic logging** if structured logging causes issues
3. **Disable alert policies** if false positives occur
4. **Rollback to previous deployment** if necessary

## Success Criteria

Phase 1 is considered successful when:

- [ ] All endpoints are monitored with basic metrics
- [ ] OpenAI API calls are tracked (cost, tokens, latency)
- [ ] Rate limiting effectiveness is monitored
- [ ] Error rates are tracked and alerted
- [ ] Structured logging is implemented
- [ ] Basic dashboards are available
- [ ] Alert policies are active and tested

## Next Steps After Phase 1

Once Phase 1 is complete and stable:

1. **Review metrics** and adjust thresholds
2. **Optimize alert policies** based on real usage
3. **Create custom dashboards** for different audiences
4. **Plan Phase 2** (distributed tracing) if needed
5. **Document lessons learned** for future phases

## Estimated Timeline

- **Step 1 (Deploy)**: 1 day
- **Step 2 (Built-in Metrics)**: 1 day
- **Step 3 (Custom Metrics)**: 2-3 days
- **Step 4 (Alerting)**: 1-2 days
- **Step 5 (Logging)**: 1-2 days
- **Testing & Verification**: 1-2 days

**Total Estimated Time**: 7-11 days
