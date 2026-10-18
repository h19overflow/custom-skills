---
name: trace-observability-integrator
description: Instruments agent workflows with standard OpenInference / OpenTelemetry distributed tracing and configures MCP _meta context propagation across Langfuse, Arize Phoenix, and LangSmith. Use whenever instrumenting agent codebases, setting up distributed tracing across client-server MCP tools, capturing tool call spans, or integrating OTLP collectors.
version: 1.0.0
---

# Trace Observability Integrator

You are a Principal AI Distributed Systems & Observability Engineer. Your responsibility is to instrument agent codebases with OpenInference semantic conventions and OpenTelemetry (OTel) context propagation, ensuring every sub-agent delegation, RAG retrieval, tool execution, and Model Context Protocol (MCP) call flows into a single unified trace tree.

---

## 1. End-to-End Distributed Tracing Topology

```
 [User Prompt / Task]
           │
           ▼
     [AGENT Span] (Session ID, User ID, Contract ID)
           │
     ┌─────┴────────────────────────────────┐
     ▼                                      ▼
[RETRIEVER Span]                     [LLM Generation Span]
 (Query, Docs, Chunk IDs)             (Prompt, Tokens, Model, Latency)
                                            │
                                            ▼
                                     [TOOL Call Span]
                                            │
                               (Propagate Trace Context 
                                via MCP "_meta" Object)
                                            │
                                            ▼
                                    [MCP Server Span]
                                (DB Query / Bash Execution)
```

Without context propagation, calls across MCP servers produce fragmented, disconnected spans. Injecting the W3C `traceparent` header into the MCP JSON-RPC `_meta` object unifies local agent orchestration with remote tool execution into one continuous trace.

---

## 2. OpenInference Span Attributes & Semantic Conventions

Every instrumented span must declare its standard OpenInference kind and core attributes:

| Span Kind | Semantic Kind Attribute | Required Context Attributes | Example Values |
| :--- | :--- | :--- | :--- |
| **AGENT** | `openinference.span.kind = "AGENT"` | `session.id`, `user.id`, `input.value`, `output.value` | `"sess_prod_102"`, `"user_883"` |
| **TOOL** | `openinference.span.kind = "TOOL"` | `tool.name`, `tool.parameters`, `tool.output`, `tool.status` | `"calculate_refund"`, `{"order_id": "ord_1"}` |
| **LLM** | `openinference.span.kind = "LLM"` | `llm.model_name`, `llm.token_count.prompt`, `llm.token_count.completion` | `"gpt-4o"`, `gemini-1.5-pro` |
| **RETRIEVER** | `openinference.span.kind = "RETRIEVER"` | `input.value`, `retrieval.documents` (with chunk IDs & contents) | `"refund policy"`, `[{"id": "doc1", "text": "..."}]` |
| **CHAIN** | `openinference.span.kind = "CHAIN"` | `chain.name`, `input.value`, `output.value` | `"planning_step"` |

---

## 3. Execution Protocol

### Step 1: Detect Active Platform Backend
Check current environment credentials:
- **Langfuse**: `LANGFUSE_PUBLIC_KEY` & `LANGFUSE_SECRET_KEY` $\to$ OTLP endpoint: `${LANGFUSE_HOST}/api/public/otel/v1/traces`
- **Arize Phoenix**: `PHOENIX_COLLECTOR_ENDPOINT` $\to$ default: `http://localhost:6006/v1/traces`
- **LangSmith**: `LANGSMITH_API_KEY` & `LANGSMITH_TRACING=true` $\to$ endpoint: `https://api.smith.langchain.com/otel/v1/traces`
- **Local/Console**: When no platform is configured, provide an in-memory/console exporter for testing without crashing.

### Step 2: Implement Telemetry Initializer (`observability/telemetry.py`)
Establish the global `TracerProvider`, attach standard OpenTelemetry resources (`service.name`, `service.version`), configure `BatchSpanProcessor`, and export via OTLP HTTP.

### Step 3: Implement MCP Context Propagation (`observability/mcp_interceptor.py`)
Use OpenTelemetry's `TraceContextTextMapPropagator` to inject the W3C `traceparent` into the MCP request payload under `_meta.traceparent`.

### Step 4: Wrap Agent Invocations & Tool Calls
Instrument the agent loop so:
1. The root task opens an `AGENT` span.
2. Retrieved knowledge chunks open a `RETRIEVER` span with document metadata.
3. Every tool call opens a `TOOL` span and dispatches MCP requests with the injected `_meta` object.

---

## 4. Implementation Code Templates

### A. Telemetry Initializer (`observability/telemetry.py`)

```python
import os
import base64
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

def init_observability(service_name: str = "agent-service") -> trace.Tracer:
    """Configures OpenInference-compliant OpenTelemetry tracing across Langfuse, Phoenix, or LangSmith."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0"
    })
    provider = TracerProvider(resource=resource)

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
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, headers=headers)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        # Development / offline fallback
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
```

### B. MCP Context Interceptor (`observability/mcp_interceptor.py`)

```python
import json
from typing import Any, Dict
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def inject_mcp_trace_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Injects W3C traceparent context into an MCP JSON-RPC call payload under the standard '_meta' key.
    Enables downstream MCP servers (SQLite, Filesystem, GitHub, Bash) to continue the parent trace.
    """
    carrier: Dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)

    if "_meta" not in payload or not isinstance(payload["_meta"], dict):
        payload["_meta"] = {}

    if "traceparent" in carrier:
        payload["_meta"]["traceparent"] = carrier["traceparent"]

    return payload

def extract_mcp_trace_context(payload: Dict[str, Any]):
    """Extracts parent trace context from incoming MCP payload for server-side handlers."""
    meta = payload.get("_meta", {})
    if isinstance(meta, dict) and "traceparent" in meta:
        carrier = {"traceparent": meta["traceparent"]}
        return TraceContextTextMapPropagator().extract(carrier)
    return None

def trace_tool_execution(tracer: trace.Tracer, tool_name: str, tool_args: Dict[str, Any]):
    """Context manager wrapping tool calls with OpenInference semantics."""
    return tracer.start_as_current_span(
        f"tool:{tool_name}",
        attributes={
            "openinference.span.kind": "TOOL",
            "tool.name": tool_name,
            "tool.parameters": json.dumps(tool_args),
        }
    )
```

---

## 5. Validation Gate

Before marking instrumentation complete:
1. **Hierarchy Check**: Verify tool calls nest under root `AGENT` spans as child spans.
2. **MCP Linking**: Call `inject_mcp_trace_context()` and verify `payload["_meta"]["traceparent"]` is populated with a valid W3C traceparent (format: `00-<trace_id>-<span_id>-01`).
3. **OpenInference Conformity**: Confirm all spans include the `openinference.span.kind` attribute.
4. **Verification Script**: Run the bundled self-test script:
   ```bash
   uv run ~/.agents/skills/trace-observability-integrator/scripts/verify_tracing.py
   ```
