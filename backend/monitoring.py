"""
Monitoring module for custom metrics and logging.

This module provides:
- Google Cloud Monitoring integration
- Custom metrics for OpenAI API usage
- Rate limiting metrics
- Performance tracking
- Error monitoring
"""

import os
import time
import datetime
import logging
from typing import Dict, Any, Optional

from google.cloud import monitoring_v3
from google.cloud.monitoring_v3.types.metric import metric_pb2
from google.cloud.monitoring_v3.types import TimeSeries, Point
from google.protobuf.timestamp_pb2 import Timestamp
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoBotMetrics:
    """Custom metrics for Memo Bot application.
    
    Provides integration with Google Cloud Monitoring for:
    - OpenAI API usage tracking
    - Rate limiting metrics
    - Performance monitoring
    - Error tracking
    """
    
    def __init__(self):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0574433212")
        self.project_name = f"projects/{self.project_id}"
        
    def create_custom_metric(self, metric_type: str, description: str) -> None:
        """Create a custom metric descriptor.
        
        Args:
            metric_type: Type of metric to create
            description: Human-readable description
        """
        try:
            descriptor = metric_pb2.MetricDescriptor(
                type=f"custom.googleapis.com/memo_bot/{metric_type}",
                description=description,
                metric_kind=metric_pb2.MetricDescriptor.MetricKind.GAUGE,
                value_type=metric_pb2.MetricDescriptor.ValueType.DOUBLE,
                labels=[
                    metric_pb2.google_dot_api_dot_label__pb2.LabelDescriptor(key="user_id", description="User ID"),
                    metric_pb2.google_dot_api_dot_label__pb2.LabelDescriptor(key="endpoint", description="API endpoint"),
                    metric_pb2.google_dot_api_dot_label__pb2.LabelDescriptor(key="model", description="OpenAI model used"),
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
        """Record OpenAI API metrics.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint used
            model: OpenAI model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Response latency in milliseconds
            cost_usd: Estimated cost in USD
            success: Whether the API call was successful
        """
        try:
            # Create time series for each metric
            timestamp = Timestamp()
            timestamp.FromDatetime(datetime.datetime.utcnow())
            
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
                        "type": "global",
                        "labels": {
                            "project_id": self.project_id,
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
        """Record rate limiting metrics.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint
            rate_limit_hit: Whether rate limit was exceeded
            remaining_quota: Remaining quota for the user
        """
        try:
            timestamp = Timestamp()
            timestamp.FromDatetime(datetime.datetime.utcnow())
            
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
                    "type": "global",
                    "labels": {
                        "project_id": self.project_id,
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
                    "type": "global",
                    "labels": {
                        "project_id": self.project_id,
                    }
                },
                points=[Point({"value": {"double_value": float(remaining_quota)}, "interval": {"end_time": timestamp}})]
            )
            
            self.client.create_time_series(name=self.project_name, time_series=[series])
            
        except Exception as e:
            logger.error(f"Failed to record rate limit metrics: {e}")

# Global metrics instance
metrics = MemoBotMetrics()
