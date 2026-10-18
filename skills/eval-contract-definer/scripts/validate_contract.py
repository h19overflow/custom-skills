# /// script
# dependencies = [
#   "pyyaml>=6.0",
# ]
# ///
"""
Validates an .evals/contract.yaml or .evals/contract.json specification against
the 6-phase evaluation metamodel.
Run with: uv run validate_contract.py <path>
Or:       python validate_contract.py <path>
"""

import sys
import json
import os

REQUIRED_TOP_LEVEL = [
    "version",
    "contract_id",
    "telemetry",
    "budgets",
    "trajectory_policy",
    "tool_contracts",
    "eval_checks",
    "ci_gates"
]

VALID_VERIFIERS = {"code_assertion", "trajectory_rule", "agent_judge"}
VALID_SEVERITIES = {"blocker", "critical", "high", "medium", "low"}

def load_contract(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Contract file not found at: {path}")

    _, ext = os.path.splitext(path.lower())
    if ext in [".yaml", ".yml"]:
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            raise ImportError(
                "PyYAML is required for .yaml files. Run with: `uv run python validate_contract.py <path>`"
            )
    else:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

def validate_contract(path: str) -> bool:
    print(f"[eval-contract-definer] Validating: {path}")
    try:
        data = load_contract(path)
    except Exception as e:
        print(f"FAIL: Load error: {e}")
        return False

    errors = []

    # 1. Top level keys
    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")

    # 2. Tool contracts
    tools = data.get("tool_contracts", {})
    if not isinstance(tools, dict) or len(tools) == 0:
        errors.append("tool_contracts must be a non-empty dictionary of tool definitions.")
    else:
        for tool_name, spec in tools.items():
            params = spec.get("parameters")
            if not params or not isinstance(params, dict):
                errors.append(f"Tool '{tool_name}' must define a standard JSON Schema 'parameters' object.")
            elif params.get("type") != "object":
                errors.append(f"Tool '{tool_name}' parameters schema must be of type 'object'.")

    # 3. Trajectory policy & transition completeness
    traj = data.get("trajectory_policy", {})
    transitions = traj.get("allowed_transitions", [])
    known_tools = set(tools.keys()) | {"START", "END"}
    for step in transitions:
        from_node = step.get("from")
        if from_node not in known_tools:
            errors.append(f"Transition 'from: {from_node}' is not declared in tool_contracts.")
        for target in step.get("can_call", []):
            if target not in known_tools:
                errors.append(f"Transition target '{target}' from '{from_node}' is not declared in tool_contracts.")

    # 4. Eval checks verifiers
    checks = data.get("eval_checks", [])
    if not isinstance(checks, list) or len(checks) == 0:
        errors.append("eval_checks must contain at least one evaluation check.")
    for idx, check in enumerate(checks):
        check_id = check.get("id", f"check_{idx}")
        verifier = check.get("verifier")
        if verifier not in VALID_VERIFIERS:
            errors.append(f"Check '{check_id}' invalid verifier '{verifier}'. Must be one of: {VALID_VERIFIERS}")
        sev = check.get("severity")
        if sev not in VALID_SEVERITIES:
            errors.append(f"Check '{check_id}' invalid severity '{sev}'. Must be one of: {VALID_SEVERITIES}")

    # 5. Telemetry
    telem = data.get("telemetry", {})
    if not telem.get("required_attributes"):
        errors.append("telemetry must define 'required_attributes' for OTel span propagation.")

    if errors:
        print(f"FAIL: {len(errors)} contract validation errors found:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("PASS: Contract is valid and adheres to the multi-tier evaluation specification.")
    return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ".evals/contract.yaml"
    success = validate_contract(target)
    sys.exit(0 if success else 1)
