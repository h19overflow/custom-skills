# /// script
# dependencies = [
#   "opentelemetry-api>=1.25.0",
#   "opentelemetry-sdk>=1.25.0",
#   "opentelemetry-exporter-otlp-proto-http>=1.25.0",
# ]
# ///
"""
OpenInference / OpenTelemetry Initialization (telemetry.py)
Configures distributed tracing for agent workflows with automated exporter routing.
"""

import os
import base64
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

def init_observability(service_name: str = "agent-service", in_memory_exporter=None) -> trace.Tracer:
    """
    Configures OpenInference-compliant OpenTelemetry tracing.
    Detects Langfuse, Arize Phoenix, or LangSmith from environment variables.
    """
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0"
    })
    provider = TracerProvider(resource=resource)

    if in_memory_exporter:
        provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))
        trace.set_tracer_provider(provider)
        return trace.get_tracer(service_name)

    otlp_endpoint: Optional[str] = None
    headers: dict = {}

    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        base_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
        otlp_endpoint = f"{base_host}/api/public/otel/v1/traces"
        creds = f"{os.getenv('LANGFUSE_PUBLIC_KEY')}:{os.getenv('LANGFUSE_SECRET_KEY')}"
        auth = base64.b64encode(creds.encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
    elif os.getenv("PHOENIX_COLLECTOR_ENDPOINT"):
        otlp_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    elif os.getenv("LANGSMITH_TRACING", "").lower() == "true":
        otlp_endpoint = "https://api.smith.langchain.com/otel/v1/traces"
        headers = {"x-api-key": os.getenv("LANGSMITH_API_KEY", "")}

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, headers=headers)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as e:
            print(f"[Telemetry] Warning: Failed to initialize OTLPSpanExporter ({e}). Falling back to console.")
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        # Development / offline fallback
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
