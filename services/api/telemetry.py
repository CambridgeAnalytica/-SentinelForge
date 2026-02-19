"""
OpenTelemetry instrumentation for SentinelForge API.

Sets up tracing (OTLP → Jaeger) and metrics (Prometheus).
"""

import logging
from functools import lru_cache

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

logger = logging.getLogger("sentinelforge.telemetry")

_RESOURCE = Resource.create(
    {
        SERVICE_NAME: "sentinelforge-api",
        SERVICE_VERSION: "2.2.0",
        "deployment.environment": "production",
    }
)


def setup_telemetry(otlp_endpoint: str = "http://localhost:4318") -> None:
    """Initialize OpenTelemetry tracing and metrics exporters."""

    # ── Tracing ──
    tracer_provider = TracerProvider(resource=_RESOURCE)
    span_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ──
    metric_exporter = OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter, export_interval_millis=30000
    )
    meter_provider = MeterProvider(resource=_RESOURCE, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    logger.info(f"✅ OpenTelemetry initialized (endpoint={otlp_endpoint})")


@lru_cache
def get_tracer(name: str = "sentinelforge") -> trace.Tracer:
    """Get a named tracer instance."""
    return trace.get_tracer(name)


@lru_cache
def get_meter(name: str = "sentinelforge") -> metrics.Meter:
    """Get a named meter instance."""
    return metrics.get_meter(name)
