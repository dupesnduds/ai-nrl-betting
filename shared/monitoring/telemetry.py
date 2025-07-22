"""Comprehensive telemetry and monitoring module with OpenTelemetry integration."""

import logging
import time
from datetime import datetime
from typing import Dict, Optional, Any, List
from functools import wraps
import structlog
import os

from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource

from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server


prediction_requests_total = Counter(
    'prediction_requests_total',
    'Total number of prediction requests',
    ['model_type', 'prediction_type', 'status', 'team_home', 'team_away']
)

prediction_request_duration_seconds = Histogram(
    'prediction_request_duration_seconds',
    'Duration of prediction requests in seconds',
    ['model_type', 'prediction_type'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

model_prediction_duration_seconds = Histogram(
    'model_prediction_duration_seconds',
    'Duration of individual model predictions in seconds',
    ['model_type'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

moe_routing_confidence = Histogram(
    'moe_routing_confidence',
    'MoE routing confidence scores',
    ['routing_strategy'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

moe_model_selections_total = Counter(
    'moe_model_selections_total',
    'Total number of model selections by MoE router',
    ['model_type', 'routing_strategy', 'forced']
)

prediction_models_available = Gauge(
    'prediction_models_available',
    'Number of prediction models currently available'
)

model_accuracy = Gauge(
    'model_accuracy',
    'Current accuracy of prediction models',
    ['model_type']
)

prediction_errors_total = Counter(
    'prediction_errors_total',
    'Total number of prediction errors',
    ['model_type', 'error_type']
)

prediction_results_total = Counter(
    'prediction_results_total',
    'Total number of prediction results by outcome',
    ['model_type', 'predicted_winner', 'prediction_type']
)

batch_prediction_size = Histogram(
    'batch_prediction_size',
    'Size of batch prediction requests',
    buckets=[1, 5, 10, 15, 20, 25]
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['cache_type', 'operation', 'hit_miss']
)

event_bus_messages_total = Counter(
    'event_bus_messages_total',
    'Total event bus messages',
    ['event_type', 'status']
)

system_info = Info(
    'prediction_engine_info',
    'Information about the prediction engine'
)


def setup_telemetry(service_name: str) -> tuple:
    """Set up OpenTelemetry tracing and metrics."""
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENVIRONMENT", "production")
    })
    
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(service_name)
    
    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://jaeger:14250",
            insecure=True
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
    except Exception as e:
        logging.warning(f"Could not set up OTLP exporter: {e}")
    
    metric_reader = PrometheusMetricReader()
    metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader], resource=resource))
    meter = metrics.get_meter(service_name)
    
    set_global_textmap(B3MultiFormat())
    
    system_info.info({
        'service_name': service_name,
        'version': '1.0.0',
        'environment': 'production'
    })
    
    return tracer, meter


def instrument_fastapi(app, service_name: str):
    """Instrument FastAPI application with OpenTelemetry."""
    FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())
    
    RequestsInstrumentor().instrument()
    try:
        SQLAlchemyInstrumentor().instrument()
    except Exception:
        pass


def setup_structured_logging(service_name: str):
    """Set up structured logging with correlation IDs."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(service_name)


class MetricsCollector:
    """Centralized metrics collection."""
    
    @staticmethod
    def record_prediction_request(
        model: str,
        prediction_type: str = "match_winner",
        status: str = "success",
        team_home: str = "",
        team_away: str = ""
    ):
        """Record a prediction request."""
        prediction_requests_total.labels(
            model_type=model,
            prediction_type=prediction_type,
            status=status,
            team_home=team_home,
            team_away=team_away
        ).inc()
    
    @staticmethod
    def record_prediction_latency(model: str, duration: float, prediction_type: str = "match_winner"):
        """Record prediction latency."""
        prediction_request_duration_seconds.labels(
            model_type=model,
            prediction_type=prediction_type
        ).observe(duration)
    
    @staticmethod
    def record_model_prediction_latency(model: str, duration: float):
        """Record individual model prediction latency."""
        model_prediction_duration_seconds.labels(model_type=model).observe(duration)
    
    @staticmethod
    def record_moe_routing(
        selected_model: str,
        confidence: float,
        strategy: str,
        forced: bool = False
    ):
        """Record MoE routing decision."""
        moe_routing_confidence.labels(routing_strategy=strategy).observe(confidence)
        moe_model_selections_total.labels(
            model_type=selected_model,
            routing_strategy=strategy,
            forced=str(forced).lower()
        ).inc()
    
    @staticmethod
    def update_available_models(count: int):
        """Update count of available models."""
        prediction_models_available.set(count)
    
    @staticmethod
    def update_model_accuracy(model: str, accuracy: float):
        """Update model accuracy."""
        model_accuracy.labels(model_type=model).set(accuracy)
    
    @staticmethod
    def record_prediction_error(model: str, error_type: str):
        """Record prediction error."""
        prediction_errors_total.labels(
            model_type=model,
            error_type=error_type
        ).inc()
    
    @staticmethod
    def record_prediction_result(
        model: str,
        predicted_winner: str,
        prediction_type: str = "match_winner"
    ):
        """Record prediction result."""
        prediction_results_total.labels(
            model_type=model,
            predicted_winner=predicted_winner,
            prediction_type=prediction_type
        ).inc()
    
    @staticmethod
    def record_batch_prediction(size: int):
        """Record batch prediction size."""
        batch_prediction_size.observe(size)
    
    @staticmethod
    def record_cache_operation(cache_type: str, operation: str, hit: bool):
        """Record cache operation."""
        cache_operations_total.labels(
            cache_type=cache_type,
            operation=operation,
            hit_miss="hit" if hit else "miss"
        ).inc()
    
    @staticmethod
    def record_event_bus_message(event_type: str, status: str = "success"):
        """Record event bus message."""
        event_bus_messages_total.labels(
            event_type=event_type,
            status=status
        ).inc()


def monitor_prediction(model_type: str):
    """Decorator to monitor prediction functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                MetricsCollector.record_model_prediction_latency(model_type, duration)
                MetricsCollector.record_prediction_request(model_type, status="success")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                MetricsCollector.record_model_prediction_latency(model_type, duration)
                MetricsCollector.record_prediction_error(model_type, type(e).__name__)
                MetricsCollector.record_prediction_request(model_type, status="error")
                raise
                
        return wrapper
    return decorator


def start_metrics_server(port: int = 8000):
    """Start Prometheus metrics server."""
    try:
        start_http_server(port)
        logging.info(f"Metrics server started on port {port}")
    except Exception as e:
        logging.error(f"Failed to start metrics server: {e}")


class HealthChecker:
    """Health checking utilities."""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                if callable(check_func):
                    if hasattr(check_func, '__await__'):
                        check_result = await check_func()
                    else:
                        check_result = check_func()
                else:
                    check_result = check_func
                
                results["checks"][name] = {
                    "status": "healthy" if check_result else "unhealthy",
                    "details": check_result
                }
                
                if not check_result:
                    overall_healthy = False
                    
            except Exception as e:
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_healthy = False
        
        results["status"] = "healthy" if overall_healthy else "unhealthy"
        return results


health_checker = HealthChecker()


SLA_TARGETS = {
    "prediction-engine": {
        "availability": 0.999,
        "latency_p50": 0.1,
        "latency_p95": 0.2,
        "latency_p99": 0.5,
        "throughput": 1000
    },
    "chat-assistant": {
        "availability": 0.995,
        "latency_p95": 2.0,
        "response_quality": 0.8
    },
    "api-gateway": {
        "availability": 0.9995,
        "latency_p95": 0.05,
        "rate_limit_accuracy": 0.999
    }
}


def check_sla_compliance(service_name: str, metrics: Dict[str, float]) -> bool:
    """Check if service metrics meet SLA targets."""
    targets = SLA_TARGETS.get(service_name, {})
    
    for metric, target in targets.items():
        actual = metrics.get(metric)
        if actual is None:
            continue
            
        if metric == "availability" and actual < target:
            return False
        elif "latency" in metric and actual > target:
            return False
        elif metric in ["response_quality", "rate_limit_accuracy"] and actual < target:
            return False
    
    return True