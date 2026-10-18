# /// script
# dependencies = [
#   "opentelemetry-api>=1.25.0",
#   "opentelemetry-sdk>=1.25.0",
# ]
# ///
"""
Observability and MCP Tracing Verification (verify_tracing.py)
Validates OpenInference span hierarchy and MCP _meta traceparent propagation.
"""

import sys
import json
from opentelemetry import trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from telemetry import init_observability
from mcp_interceptor import inject_mcp_trace_context, extract_mcp_trace_context, trace_tool_execution

def main():
    print("[Observability Verifier] Starting end-to-end trace validation...")

    # 1. Setup in-memory exporter
    memory_exporter = InMemorySpanExporter()
    tracer = init_observability("test-agent-service", in_memory_exporter=memory_exporter)

    # 2. Simulate Agent Execution Flow
    session_id = "sess_verify_101"
    captured_mcp_payload = None

    with tracer.start_as_current_span("agent_root_task", attributes={
        "openinference.span.kind": "AGENT",
        "session.id": session_id,
        "input.value": "Lookup user profile and update preference",
    }) as agent_span:
        
        # A. Child Retriever Span
        with tracer.start_as_current_span("retriever_lookup", attributes={
            "openinference.span.kind": "RETRIEVER",
            "input.value": "user profile schema",
            "retrieval.documents": json.dumps([{"id": "doc_1", "text": "Profile fields"}]),
        }):
            pass

        # B. Child Tool Span with MCP Context Propagation
        tool_name = "sqlite_query"
        tool_args = {"query": "SELECT * FROM users WHERE id=1;"}
        with trace_tool_execution(tracer, tool_name, tool_args) as tool_span:
            # Inject context into outgoing MCP payload
            outgoing_payload = {"method": "tools/call", "params": tool_args}
            injected_payload = inject_mcp_trace_context(outgoing_payload)
            captured_mcp_payload = injected_payload

            # Simulate MCP Server handling the request in another process/service
            parent_ctx = extract_mcp_trace_context(injected_payload)
            with tracer.start_as_current_span("mcp_server_exec", context=parent_ctx, attributes={
                "openinference.span.kind": "TOOL",
                "mcp.server.name": "sqlite_server",
            }) as server_span:
                server_span.set_attribute("tool.output", json.dumps({"rows": 1}))

            tool_span.set_attribute("tool.output", json.dumps({"rows": 1}))

        agent_span.set_attribute("output.value", "User preference updated.")

    # 3. Assertions & Verification
    spans = memory_exporter.get_finished_spans()
    print(f"[Observability Verifier] Captured {len(spans)} finished spans.")

    assert len(spans) == 4, f"Expected 4 spans, got {len(spans)}"

    # Check Trace IDs match across all spans (unified trace)
    trace_ids = {span.context.trace_id for span in spans}
    print(f"[Observability Verifier] Distinct Trace IDs found: {len(trace_ids)}")
    assert len(trace_ids) == 1, f"Expected unified trace ID across all spans, found multiple: {trace_ids}"

    # Check MCP traceparent was injected
    assert captured_mcp_payload is not None
    meta = captured_mcp_payload.get("_meta", {})
    traceparent = meta.get("traceparent")
    print(f"[Observability Verifier] Injected MCP traceparent: {traceparent}")
    assert traceparent is not None, "Failed to inject W3C traceparent into MCP _meta"
    assert traceparent.startswith("00-"), "Invalid W3C traceparent version prefix"

    # Check OpenInference kinds
    span_kinds = {span.name: span.attributes.get("openinference.span.kind") for span in spans}
    print(f"[Observability Verifier] OpenInference span kinds: {span_kinds}")
    assert span_kinds.get("agent_root_task") == "AGENT"
    assert span_kinds.get("retriever_lookup") == "RETRIEVER"
    assert span_kinds.get("tool:sqlite_query") == "TOOL"
    assert span_kinds.get("mcp_server_exec") == "TOOL"

    print("\n✅ ALL VERIFICATION CHECKS PASSED: OpenInference hierarchy and MCP context propagation verified!")
    sys.exit(0)

if __name__ == "__main__":
    main()
