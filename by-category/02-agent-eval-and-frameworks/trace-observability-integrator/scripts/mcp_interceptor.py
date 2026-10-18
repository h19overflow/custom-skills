# /// script
# dependencies = [
#   "opentelemetry-api>=1.25.0",
#   "opentelemetry-sdk>=1.25.0",
# ]
# ///
"""
MCP Context Propagation Interceptor (mcp_interceptor.py)
Injects and extracts W3C trace context into Model Context Protocol (MCP) _meta payloads.
"""

import json
from typing import Any, Dict, Optional
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def inject_mcp_trace_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Injects W3C traceparent context into an MCP JSON-RPC payload under '_meta.traceparent'.
    Ensures downstream MCP servers continue the parent trace tree.
    """
    carrier: Dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)

    if "_meta" not in payload or not isinstance(payload["_meta"], dict):
        payload["_meta"] = {}

    if "traceparent" in carrier:
        payload["_meta"]["traceparent"] = carrier["traceparent"]

    return payload

def extract_mcp_trace_context(payload: Dict[str, Any]) -> Optional[Any]:
    """
    Extracts parent trace context from incoming MCP payload for server-side handlers.
    Returns Context object suitable for tracer.start_as_current_span(..., context=parent_context).
    """
    meta = payload.get("_meta", {})
    if isinstance(meta, dict) and "traceparent" in meta:
        carrier = {"traceparent": meta["traceparent"]}
        return TraceContextTextMapPropagator().extract(carrier)
    return None

def trace_tool_execution(tracer: trace.Tracer, tool_name: str, tool_args: Dict[str, Any]):
    """
    Context manager wrapping tool execution with OpenInference TOOL semantics.
    """
    return tracer.start_as_current_span(
        f"tool:{tool_name}",
        attributes={
            "openinference.span.kind": "TOOL",
            "tool.name": tool_name,
            "tool.parameters": json.dumps(tool_args),
        }
    )
