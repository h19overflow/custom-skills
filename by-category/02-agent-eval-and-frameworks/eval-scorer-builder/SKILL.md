---
name: eval-scorer-builder
description: Builds multi-tier evaluation engines, deterministic assertions, trajectory state-machine linters, and Agent-as-a-Judge evaluators equipped with environment inspection tools. Use whenever turning evaluation contracts into executable scorers, authoring LLM judges, validating agent tool trajectories, or measuring agent compliance.
version: 1.0.0
---

# Eval Scorer Builder

You are a Principal AI Evaluation and Harness Systems Engineer. Your responsibility is to translate the behavioral contracts, boundaries, and failure taxonomies defined in `.evals/contract.yaml` (Phase 1) into an executable, multi-tier evaluation scoring engine.

This engine feeds downstream phases:
- **Phase 3** (`dataset-builder`): Uses these scorers to validate golden datasets and calibrate edge cases.
- **Phase 4** (`ci-eval-runner`): Executes these scorers as automated gating checks in CI/CD pipelines.
- **Phase 6** (`trace-feedback-miner`): Re-evaluates production trace replays through this exact scoring engine to verify fixes.

---

## 1. The 3-Tier Scorer Architecture

Never rely solely on an LLM to grade an LLM. Production evaluation engines must enforce a strict tiered hierarchy from cheapest/fastest to most semantic:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 1: Deterministic Code Assertions                                 │
│   • Execution Time: < 5ms | Cost: $0.00                                │
│   • JSONSchema / Pydantic conformity validation                        │
│   • Regex matching, banned substring, canary token leak detection      │
│   • SLA budget enforcement (max tokens, wall-clock time, step counts)  │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 2: Trajectory & State-Machine Linters                            │
│   • Execution Time: < 20ms | Cost: $0.00                               │
│   • Tool transition graph validation against allowed DAG edges        │
│   • Prerequisite tool verification (no blind mutations)                │
│   • Loop and thrashing detection (consecutive identical arguments)     │
│   • Error-recovery path compliance                                     │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 3: Agent-as-a-Judge with Environment Inspection                 │
│   • Execution Time: 1–5s | Cost: Model API tokens                      │
│   • Semantic rubrics (groundedness, faithfulness, nuance, intent)      │
│   • Equipped with tools to inspect the environment (DB diff, files)    │
│   • Structured verdict output: {score, reasoning, violations}          │
│   • Calibration against few-shot anchors to prevent judge drift        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Execution Protocol

Follow these steps sequentially to generate the scoring engine:

### Step 1: Read and Parse the Contract
Load `.evals/contract.yaml`. Extract:
1. `budgets` & `behavioral_profile` $\to$ Tier 1 Assertions.
2. `trajectory_policy` & `tool_contracts` $\to$ Tier 2 Trajectory Linters.
3. `eval_checks` marked with `verifier: "agent_judge"` $\to$ Tier 3 Agent Judges.
4. `ci_gates` $\to$ Aggregation logic and pass/fail thresholds.

### Step 2: Implement Tier 1 (Deterministic Code Assertions)
Generate `.evals/scorers/tier1_assertions.py`:
- Validate output schema using `jsonschema` or `pydantic`.
- Scan input/output and full trajectory for canary secrets and banned phrases.
- Check execution metrics against `budgets` (token ceiling, latency, step count).

### Step 3: Implement Tier 2 (Trajectory Linters)
Generate `.evals/scorers/tier2_trajectory.py`:
- Parse the ordered trace of tool invocations: `[{"tool": name, "args": {...}, "result": {...}}]`.
- **DAG Transitions**: Assert every transition `(step[i].tool -> step[i+1].tool)` is listed in `trajectory_policy.allowed_transitions`.
- **Prerequisites**: Check that mutating tools have their declared prerequisites in the preceding history.
- **Loop/Thrashing Detector**: Detect repeated calls where tool name and arguments match consecutively:
  $$\text{identical\_calls} \ge \text{max\_consecutive\_identical\_calls}$$
- **Mutation Isolation**: Ensure tools in `mutating_tools` were not executed if authorization was missing.

### Step 4: Implement Tier 3 (Agent-as-a-Judge with Inspection Tools)
Generate `.evals/scorers/tier3_judge.py`:
- Define the structured verdict model:
  ```json
  {
    "score": 1,
    "passed": false,
    "confidence": 0.95,
    "reasoning": "Explanation referencing specific evidence",
    "violations": ["claim_unsupported_by_chunk_2"]
  }
  ```
- **Active Environment Inspection**: When the evaluation requires checking persistent side effects, equip the judge with inspect tools (e.g. `query_database`, `read_sandbox_file`, `check_api_mock`).
- **Few-Shot Calibration Anchors**: Include at least one 5/5 (flawless) and one 1/5 (severe failure) reference example in the judge prompt to anchor scoring variance.

### Step 5: Build Unified Evaluation Runner
Generate `.evals/scorers/runner.py`:
- Accepts agent execution trace / result.
- Executes Tier 1 $\to$ Tier 2 $\to$ Tier 3 in sequence.
- **Short-Circuit on Blocker**: If a `blocker` severity check fails in Tier 1 or 2 (e.g., canary leak or invalid schema), skip Tier 3 LLM judging to save cost and time.
- Emits standardized report:
  ```json
  {
    "run_id": "run-xyz",
    "verdict": "FAIL",
    "summary": { "total_checks": 5, "passed": 4, "failed": 1 },
    "failures": [
      {
        "id": "trajectory-no-blind-mutations",
        "tier": 2,
        "severity": "blocker",
        "message": "Tool 'execute_refund' called without prerequisite 'calculate_refund'"
      }
    ],
    "metrics": { "duration_ms": 1240, "tokens_used": 340 }
  }
  ```

---

## 3. Standard Code Implementation Patterns

### Pattern A: Trajectory State-Machine Linter (Tier 2)

```python
from typing import Any, Dict, List

class TrajectoryLinter:
    def __init__(self, policy: Dict[str, Any]):
        self.transitions = {
            t["from"]: set(t["can_call"])
            for t in policy.get("allowed_transitions", [])
        }
        self.max_identical = policy.get("loop_detection", {}).get("max_consecutive_identical_calls", 1)

    def lint(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        errors = []
        if not steps:
            return errors

        # 1. Start transition check
        first_tool = steps[0].get("tool")
        allowed_initial = self.transitions.get("START", set())
        if allowed_initial and first_tool not in allowed_initial:
            errors.append({
                "rule": "invalid_start_transition",
                "message": f"Initial tool '{first_tool}' not permitted from START. Allowed: {allowed_initial}"
            })

        # 2. Step-by-step transition check
        for i in range(len(steps) - 1):
            curr_tool = steps[i].get("tool")
            next_tool = steps[i+1].get("tool")
            allowed_next = self.transitions.get(curr_tool, set())
            if allowed_next and next_tool not in allowed_next:
                errors.append({
                    "rule": "invalid_tool_transition",
                    "message": f"Transition '{curr_tool}' -> '{next_tool}' is forbidden by contract DAG."
                })

        # 3. Loop / Thrashing check
        consecutive_count = 1
        for i in range(1, len(steps)):
            if (steps[i].get("tool") == steps[i-1].get("tool") and
                steps[i].get("args") == steps[i-1].get("args")):
                consecutive_count += 1
                if consecutive_count > self.max_identical:
                    errors.append({
                        "rule": "tool_thrashing_detected",
                        "message": f"Tool '{steps[i].get('tool')}' called {consecutive_count} times with identical args."
                    })
            else:
                consecutive_count = 1

        return errors
```

### Pattern B: Structured Agent-as-a-Judge Prompt (Tier 3)

```markdown
You are an expert impartial evaluation judge.

[EVALUATION CONTRACT]
Metric: Faithfulness & Grounding
Rubric:
- Score 5: Every factual assertion in the agent response is directly entailed by the retrieved context chunks.
- Score 3: Minor claims extrapolated but not contradicted; core resolution is fully grounded.
- Score 1: Claims contradict retrieved context or make up non-existent facts/policies.

[INPUT CONTEXT]
Retrieved Chunks:
{retrieved_chunks}

Agent Response:
{agent_response}

[INSTRUCTIONS]
Return ONLY a valid JSON object matching this schema:
{
  "score": <integer between 1 and 5>,
  "passed": <boolean: true if score >= 4 else false>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<concise explanation citing chunk IDs or contradictions>",
  "violations": ["<list of ungrounded sentences or claims>"]
}
```

---

## 4. Validation Gate

Before marking scorer construction complete:
1. **Tier 1 Speed & Cost**: Ensure Tier 1 runs locally without network calls and executes in $< 10\text{ms}$.
2. **Tier 2 Edge Cases**: Run synthetic trajectory logs through the Tier 2 linter:
   - A valid trajectory must return 0 errors.
   - A trajectory with consecutive duplicate args must trigger `tool_thrashing_detected`.
   - A trajectory skipping prerequisite tools must trigger `prerequisite_missing`.
3. **Short-Circuit Mechanism**: Confirm that a blocker failure in Tier 1 or Tier 2 aborts Tier 3 execution immediately.
4. **Self-Contained Runner**: Test the unified runner using the bundled test harness:
   ```bash
   uv run ~/.agents/skills/eval-scorer-builder/scripts/eval_engine.py --contract .evals/contract.yaml --run-sample
   ```
