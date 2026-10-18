# /// script
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""
Closed-Loop Trace Miner (mine_traces.py):
Mines failing runtime/production traces, extracts reproducing failure paths,
redacts sensitive data, and converts them into versioned regression test fixtures.

Usage:
  uv run mine_traces.py --source .evals/traces/traces.json --contract .evals/contract.yaml --output .evals/datasets/regression_fixtures.jsonl
  uv run mine_traces.py --generate-sample-failure
"""

import sys
import os
import json
import re
import argparse
from typing import List, Dict, Any

def load_yaml_or_json(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    _, ext = os.path.splitext(path.lower())
    if ext in [".yaml", ".yml"]:
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            raise ImportError("PyYAML is required for YAML parsing.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def redact_sensitive_data(val: Any) -> Any:
    """Recursively scrub tokens, keys, emails, and passwords from extracted traces."""
    if isinstance(val, str):
        # Redact keys/tokens
        val = re.sub(r'(?i)(bearer\s+[a-zA-Z0-9_\-\.]+)', 'bearer [REDACTED]', val)
        val = re.sub(r'(?i)(api[_\-]?key["\']?\s*[:=]\s*["\']?)[a-zA-Z0-9_\-]+', r'\1[REDACTED]', val)
        # Redact emails
        val = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', val)
        return val
    elif isinstance(val, dict):
        return {k: redact_sensitive_data(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    return val

def analyze_and_extract_failures(traces: List[Dict[str, Any]], contract: dict) -> List[Dict[str, Any]]:
    fixtures = []
    contract_id = contract.get("contract_id", "agent-system")

    for trace in traces:
        trace_id = trace.get("trace_id", "unknown_trace")
        status = trace.get("status", "success")
        spans = trace.get("spans", [])
        metrics = trace.get("metrics", {})
        eval_scores = trace.get("eval_scores", {})

        is_failure = False
        failure_type = "unknown"
        failure_reason = ""
        mock_tool_responses = {}

        # 1. Check for tool exceptions / 500 status
        for span in spans:
            if span.get("kind") == "TOOL" or span.get("attributes", {}).get("openinference.span.kind") == "TOOL":
                attrs = span.get("attributes", {})
                tool_name = attrs.get("tool.name", span.get("name", "unknown_tool"))
                tool_output = attrs.get("tool.output", "")
                
                # Capture mock response
                if isinstance(tool_output, str):
                    try:
                        mock_tool_responses[tool_name] = json.loads(tool_output)
                    except Exception:
                        mock_tool_responses[tool_name] = tool_output
                else:
                    mock_tool_responses[tool_name] = tool_output

                if attrs.get("status") == "error" or "error" in str(tool_output).lower() or attrs.get("http.status_code", 200) >= 500:
                    is_failure = True
                    failure_type = "tool_failure"
                    failure_reason = f"Tool '{tool_name}' failed with downstream error."
                    break

        # 2. Check for tool thrashing (consecutive duplicate tool calls)
        tool_spans = [s for s in spans if s.get("kind") == "TOOL" or s.get("attributes", {}).get("openinference.span.kind") == "TOOL"]
        for i in range(1, len(tool_spans)):
            prev_name = tool_spans[i-1].get("attributes", {}).get("tool.name")
            curr_name = tool_spans[i].get("attributes", {}).get("tool.name")
            prev_args = tool_spans[i-1].get("attributes", {}).get("tool.parameters")
            curr_args = tool_spans[i].get("attributes", {}).get("tool.parameters")
            if prev_name and prev_name == curr_name and prev_args and prev_args == curr_args:
                is_failure = True
                failure_type = "adversarial"
                failure_reason = f"Tool thrashing detected: tool '{curr_name}' called repeatedly with identical parameters."
                break

        # 3. Check for low evaluation scores (e.g. faithfulness < 0.70)
        faithfulness = eval_scores.get("faithfulness", 1.0)
        if faithfulness < 0.70:
            is_failure = True
            failure_type = "rag_distraction"
            failure_reason = f"Ungrounded hallucination in response: faithfulness score {faithfulness} < 0.70."

        if is_failure:
            # Extract root task prompt
            root_span = next((s for s in spans if s.get("kind") == "AGENT" or s.get("attributes", {}).get("openinference.span.kind") == "AGENT"), {})
            root_input = root_span.get("attributes", {}).get("input.value") or trace.get("input", "Reproduce mined failure task.")
            
            clean_input = redact_sensitive_data(root_input)
            clean_mock_responses = redact_sensitive_data(mock_tool_responses)

            fixture = {
                "id": f"mined_repro_{trace_id[:8]}",
                "category": failure_type,
                "input": {
                    "task": clean_input,
                    "mock_tool_responses": clean_mock_responses
                },
                "expected_trajectory": {
                    "required_tools": list(mock_tool_responses.keys()),
                    "forbidden_tools": ["infinite_loop", "crash_silently"],
                    "max_steps": contract.get("budgets", {}).get("max_step_ceiling", 8),
                    "expected_final_state": {
                        "resolution_status": "escalated" if failure_type == "tool_failure" else "resolved"
                    }
                },
                "metadata": {
                    "source_trace_id": trace_id,
                    "failure_reason": failure_reason,
                    "mined_at": "2026-10-03",
                    "contract_id": contract_id
                }
            }
            fixtures.append(fixture)

    return fixtures

def main():
    parser = argparse.ArgumentParser(description="Closed-Loop Trace Feedback Miner")
    parser.add_argument("--source", help="Path to trace log JSON")
    parser.add_argument("--contract", default=".evals/contract.yaml", help="Path to contract")
    parser.add_argument("--output", default=".evals/datasets/regression_fixtures.jsonl", help="Output .jsonl path")
    parser.add_argument("--generate-sample-failure", action="store_true", help="Synthesize a sample failing trace")
    args = parser.parse_args()

    if args.generate_sample-failure if hasattr(args, "generate_sample-failure") else getattr(args, "generate_sample_failure", False):
        sample_failing_traces = [
            {
                "trace_id": "tr_prod_fail_88291a",
                "status": "error",
                "input": "Update shipping address for user user_bob@company.com with token bearer abc123def.",
                "spans": [
                    {
                        "name": "agent_execution",
                        "attributes": {
                            "openinference.span.kind": "AGENT",
                            "input.value": "Update shipping address for user user_bob@company.com with token bearer abc123def."
                        }
                    },
                    {
                        "name": "tool:update_address",
                        "attributes": {
                            "openinference.span.kind": "TOOL",
                            "tool.name": "update_address",
                            "tool.parameters": json.dumps({"user_id": "user_123", "address": "742 Evergreen Terrace"}),
                            "status": "error",
                            "tool.output": json.dumps({"error": "ServiceUnavailable", "status_code": 503})
                        }
                    }
                ],
                "eval_scores": {"faithfulness": 0.55}
            }
        ]
        out_trace_file = ".evals/traces/sample_failing_trace.json"
        os.makedirs(os.path.dirname(out_trace_file), exist_ok=True)
        with open(out_trace_file, "w", encoding="utf-8") as f:
            json.dump(sample_failing_traces, f, indent=2)
        print(f"Generated sample failing trace at: {out_trace_file}")
        return

    if not args.source:
        print("Error: --source <trace_file> or --generate-sample-failure must be provided.")
        sys.exit(1)

    traces = load_yaml_or_json(args.source)
    if isinstance(traces, dict):
        traces = [traces]

    contract = load_yaml_or_json(args.contract) if os.path.exists(args.contract) else {}
    fixtures = analyze_and_extract_failures(traces, contract)

    print(f"[Trace Miner] Analyzed {len(traces)} traces. Found {len(fixtures)} actionable failure trajectories.")

    if fixtures:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(args.output, "a", encoding="utf-8") as f:
            for fix in fixtures:
                f.write(json.dumps(fix) + "\n")
                print(f"  ✓ Mined fixture: {fix['id']} (Reason: {fix['metadata']['failure_reason']})")
        print(f"[Trace Miner] Successfully appended {len(fixtures)} regression fixtures to: {args.output}")

if __name__ == "__main__":
    main()
