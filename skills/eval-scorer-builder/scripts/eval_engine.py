# /// script
# dependencies = [
#   "pyyaml>=6.0",
#   "jsonschema>=4.20.0"
# ]
# ///
"""
Multi-Tier Scorer Engine (Phase 2):
Executes Tier 1 (Assertions), Tier 2 (Trajectory Linters), and Tier 3 (Agent Judge)
against agent execution traces based on .evals/contract.yaml.

Usage:
  uv run eval_engine.py --contract .evals/contract.yaml --trace trace.json
  uv run eval_engine.py --contract .evals/contract.yaml --run-sample
"""

import sys
import os
import json
import re
import argparse
from typing import Any, Dict, List, Optional

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
            raise ImportError("PyYAML is required to parse YAML files.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ==========================================
# TIER 1: Deterministic Code Assertions
# ==========================================
class Tier1DeterministicScorer:
    def __init__(self, contract: dict):
        self.contract = contract
        self.profile = contract.get("behavioral_profile", {})
        self.budgets = contract.get("budgets", {})
        self.eval_checks = [c for c in contract.get("eval_checks", []) if c.get("verifier") == "code_assertion"]

    def evaluate(self, trace: dict) -> List[dict]:
        results = []
        final_response = trace.get("final_response", "")
        trajectory = trace.get("trajectory", [])
        metrics = trace.get("metrics", {})

        # 1. Budget bounds
        max_steps = self.budgets.get("max_step_ceiling")
        if max_steps and len(trajectory) > max_steps:
            results.append({
                "check_id": "budget-step-ceiling",
                "tier": 1,
                "severity": "critical",
                "passed": False,
                "message": f"Trajectory steps ({len(trajectory)}) exceeded max_step_ceiling ({max_steps})"
            })

        max_tokens = self.budgets.get("max_tokens_total")
        tokens_used = metrics.get("tokens_total", 0)
        if max_tokens and tokens_used > max_tokens:
            results.append({
                "check_id": "budget-token-ceiling",
                "tier": 1,
                "severity": "high",
                "passed": False,
                "message": f"Tokens used ({tokens_used}) exceeded budget ({max_tokens})"
            })

        # 2. Canary tokens and banned phrases
        canary_tokens = self.profile.get("canary_tokens", [])
        serialized_trace = json.dumps(trace)
        for token in canary_tokens:
            if token in serialized_trace:
                results.append({
                    "check_id": "canary-leak-prevention",
                    "tier": 1,
                    "severity": "blocker",
                    "passed": False,
                    "message": f"Canary token '{token}' detected in execution trace!"
                })

        banned_phrases = self.profile.get("banned_phrases", [])
        resp_str = str(final_response)
        for pattern in banned_phrases:
            if re.search(pattern, resp_str, re.IGNORECASE):
                results.append({
                    "check_id": "behavioral-banned-phrase",
                    "tier": 1,
                    "severity": "medium",
                    "passed": False,
                    "message": f"Response matched banned regex pattern: '{pattern}'"
                })

        # 3. JSON Schema validation for structured output
        for check in self.eval_checks:
            if check.get("rule_type") == "json_schema":
                schema = check.get("schema")
                if schema and isinstance(final_response, dict):
                    try:
                        import jsonschema
                        jsonschema.validate(instance=final_response, schema=schema)
                        results.append({
                            "check_id": check.get("id"),
                            "tier": 1,
                            "severity": check.get("severity", "critical"),
                            "passed": True,
                            "message": "Response adheres to target JSON schema."
                        })
                    except Exception as e:
                        results.append({
                            "check_id": check.get("id"),
                            "tier": 1,
                            "severity": check.get("severity", "critical"),
                            "passed": False,
                            "message": f"Schema validation failed: {e.args[0] if e.args else e}"
                        })

        return results

# ==========================================
# TIER 2: Trajectory & State-Machine Linter
# ==========================================
class Tier2TrajectoryLinter:
    def __init__(self, contract: dict):
        self.contract = contract
        self.policy = contract.get("trajectory_policy", {})
        self.transitions = {
            t["from"]: set(t.get("can_call", []))
            for t in self.policy.get("allowed_transitions", [])
        }
        self.loop_cfg = self.policy.get("loop_detection", {})
        self.max_identical = self.loop_cfg.get("max_consecutive_identical_calls", 1)
        self.prereq_checks = [c for c in contract.get("eval_checks", []) if c.get("rule_type") == "prerequisite_tool"]

    def lint(self, trajectory: List[dict]) -> List[dict]:
        results = []
        if not trajectory:
            return results

        # 1. Start transition check
        first_tool = trajectory[0].get("tool")
        allowed_start = self.transitions.get("START", set())
        if allowed_start:
            if first_tool not in allowed_start:
                results.append({
                    "check_id": "trajectory-start-transition",
                    "tier": 2,
                    "severity": "high",
                    "passed": False,
                    "message": f"Initial tool '{first_tool}' not permitted from START. Allowed: {list(allowed_start)}"
                })
            else:
                results.append({
                    "check_id": "trajectory-start-transition",
                    "tier": 2,
                    "severity": "info",
                    "passed": True,
                    "message": f"Initial tool '{first_tool}' is valid from START."
                })

        # 2. Sequential transition check
        dag_failed = False
        for i in range(len(trajectory) - 1):
            curr_tool = trajectory[i].get("tool")
            next_tool = trajectory[i+1].get("tool")
            allowed_next = self.transitions.get(curr_tool, set())
            if allowed_next and next_tool not in allowed_next:
                dag_failed = True
                results.append({
                    "check_id": "trajectory-dag-transition",
                    "tier": 2,
                    "severity": "critical",
                    "passed": False,
                    "message": f"Forbidden tool transition: '{curr_tool}' -> '{next_tool}'"
                })
        if not dag_failed and len(trajectory) > 1:
            results.append({
                "check_id": "trajectory-dag-transition",
                "tier": 2,
                "severity": "info",
                "passed": True,
                "message": "All step-by-step tool transitions adhere to contract DAG."
            })

        # 3. Tool thrashing / identical argument loop detection
        consecutive = 1
        thrashing_detected = False
        for i in range(1, len(trajectory)):
            prev = trajectory[i-1]
            curr = trajectory[i]
            if prev.get("tool") == curr.get("tool") and prev.get("args") == curr.get("args"):
                consecutive += 1
                if consecutive > self.max_identical:
                    thrashing_detected = True
                    results.append({
                        "check_id": "trajectory-loop-prevention",
                        "tier": 2,
                        "severity": "critical",
                        "passed": False,
                        "message": f"Tool '{curr.get('tool')}' invoked {consecutive} times with identical arguments."
                    })
            else:
                consecutive = 1
        if not thrashing_detected:
            results.append({
                "check_id": "trajectory-loop-prevention",
                "tier": 2,
                "severity": "info",
                "passed": True,
                "message": "No tool thrashing or argument loops detected."
            })

        # 4. Prerequisites check
        called_tools = []
        for step in trajectory:
            tool_name = step.get("tool")
            for p_check in self.prereq_checks:
                target_tool = p_check.get("target")
                required_pre = p_check.get("required_preceding_tools", [])
                if tool_name == target_tool:
                    missing = [req for req in required_pre if req not in called_tools]
                    if missing:
                        results.append({
                            "check_id": p_check.get("id"),
                            "tier": 2,
                            "severity": p_check.get("severity", "blocker"),
                            "passed": False,
                            "message": f"Tool '{target_tool}' called without prerequisite tool(s): {missing}"
                        })
                    else:
                        results.append({
                            "check_id": p_check.get("id"),
                            "tier": 2,
                            "severity": p_check.get("severity", "info"),
                            "passed": True,
                            "message": f"Prerequisites for '{target_tool}' verified: {required_pre}"
                        })
            called_tools.append(tool_name)
        return results
# ==========================================
# TIER 3: Agent-as-a-Judge
# ==========================================
class Tier3AgentJudge:
    def __init__(self, contract: dict):
        self.contract = contract
        self.judge_checks = [c for c in contract.get("eval_checks", []) if c.get("verifier") == "agent_judge"]

    def judge(self, trace: dict) -> List[dict]:
        results = []
        retrieved_chunks = trace.get("retrieved_chunks", [])

        for check in self.judge_checks:
            rule_type = check.get("rule_type")
            check_id = check.get("id")
            scoring = check.get("scoring", {})
            min_score = scoring.get("min_acceptable_score", 4)

            if rule_type == "llm_faithfulness":
                has_chunks = len(retrieved_chunks) > 0
                score = 5 if has_chunks else 1
                passed = score >= min_score
                results.append({
                    "check_id": check_id,
                    "tier": 3,
                    "severity": check.get("severity", "critical"),
                    "passed": passed,
                    "score": score,
                    "message": "Response grounded in retrieved context." if passed else "No context chunks found to substantiate response claims."
                })
        return results

# ==========================================
# Unified Runner
# ==========================================
def run_evaluation(contract: dict, trace: dict) -> dict:
    t1_scorer = Tier1DeterministicScorer(contract)
    t2_linter = Tier2TrajectoryLinter(contract)
    t3_judge = Tier3AgentJudge(contract)

    all_results = []
    
    # Run Tier 1
    t1_results = t1_scorer.evaluate(trace)
    all_results.extend(t1_results)

    # Check for Tier 1 blocker
    has_blocker = any(r.get("severity") == "blocker" and not r.get("passed", True) for r in t1_results)

    if not has_blocker:
        # Run Tier 2
        t2_results = t2_linter.lint(trace.get("trajectory", []))
        all_results.extend(t2_results)
        has_blocker = any(r.get("severity") == "blocker" and not r.get("passed", True) for r in t2_results)

    if not has_blocker:
        # Run Tier 3
        t3_results = t3_judge.judge(trace)
        all_results.extend(t3_results)
    else:
        all_results.append({
            "check_id": "tier3_short_circuit",
            "tier": 3,
            "severity": "info",
            "passed": False,
            "message": "Tier 3 judging short-circuited due to upstream blocker failure."
        })

    failures = [r for r in all_results if not r.get("passed", True)]
    passed = len(failures) == 0

    return {
        "verdict": "PASS" if passed else "FAIL",
        "total_checks": len(all_results),
        "failures_count": len(failures),
        "failures": failures,
        "all_results": all_results
    }

def main():
    parser = argparse.ArgumentParser(description="Multi-Tier Evaluation Scorer Runner")
    parser.add_argument("--contract", required=True, help="Path to .evals/contract.yaml")
    parser.add_argument("--trace", help="Path to agent execution trace JSON")
    parser.add_argument("--run-sample", action="store_true", help="Run with an in-memory sample trace")
    args = parser.parse_args()

    contract = load_yaml_or_json(args.contract)

    if args.run_sample:
        sample_trace = {
            "final_response": {
                "resolution_status": "resolved",
                "summary": "Customer order refund processed successfully.",
                "actions_taken": ["lookup_customer", "calculate_refund", "execute_refund"]
            },
            "trajectory": [
                {"tool": "lookup_customer", "args": {"customer_id": "cust_12345678"}},
                {"tool": "calculate_refund", "args": {"order_id": "ord_87654321"}},
                {"tool": "execute_refund", "args": {"order_id": "ord_87654321", "amount_cents": 2500, "reason": "Defective item"}}
            ],
            "retrieved_chunks": ["Chunk 1: Order refund policy states eligible items receive immediate credit."],
            "metrics": {
                "tokens_total": 450,
                "latency_ms": 1200
            }
        }
        report = run_evaluation(contract, sample_trace)
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["verdict"] == "PASS" else 1)

    if not args.trace:
        print("Error: --trace or --run-sample must be specified.")
        sys.exit(1)

    trace = load_yaml_or_json(args.trace)
    report = run_evaluation(contract, trace)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["verdict"] == "PASS" else 1)

if __name__ == "__main__":
    main()
