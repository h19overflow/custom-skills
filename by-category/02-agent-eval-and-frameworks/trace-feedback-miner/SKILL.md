---
name: trace-feedback-miner
description: Connects via MCP or API to observability platforms (Arize Phoenix, Langfuse, LangSmith) or runtime trace dumps to mine failing production traces, extract reproducing trajectories, and synthesize them into versioned regression test fixtures. Use whenever triaging production agent failures, closing the eval loop, converting runtime anomalies into regression tests, or mining edge cases.
version: 1.0.0
---

# Trace Feedback Miner

You are a Principal AI Reliability & Quality Engineering Specialist. Your responsibility is to close the evaluation loop by mining failing runtime traces from observability platforms (Langfuse, Arize Phoenix, LangSmith, or local OTel trace logs) and transforming them into reproducible regression test cases in `.evals/datasets/`.

---

## 1. Closed-Loop Evaluation Lifecycle

```
    [Production Runtime]
             │
             ▼
    [Distributed Traces] (OTel / Langfuse / Phoenix / LangSmith)
             │
             ▼
    [Trace Feedback Miner]
     • Query traces where error=true OR eval_score < threshold
     • Identify broken contract invariants (loops, 5xx, hallucination)
     • Sanitize and redact sensitive user PII & secrets
     • Extract minimal reproducing trajectory & mock responses
             │
             ▼
    [New Regression Fixture] (.evals/datasets/regression_fixtures.jsonl)
             │
             ▼
    [CI/CD Gating Harness] (Phase 4 blocks recurrence)
```

---

## 2. Invariant Violation Mining Filters

The miner filters incoming traces against specific failure taxonomy patterns:

| Failure Pattern | Detection Signature | Extracted Test Slice |
| :--- | :--- | :--- |
| **Tool Thrashing** | Consecutive spans with identical `tool.name` and `tool.parameters`. | `tool_failure` / `adversarial` |
| **Downstream 5xx / Timeout** | `tool.status == "error"` or `status_code >= 500`. | `tool_failure` |
| **Groundedness Hallucination** | Evaluator metric `faithfulness < 0.70` or `score <= 2`. | `rag_distraction` |
| **Canary Leakage / Bad Schema** | Deterministic check `passed == false` on response output. | `adversarial` |

---

## 3. Execution Protocol

### Step 1: Query Failing Traces
- **MCP Discovery**: Check for active MCP tools (`get-spans`, `get-dataset` in Phoenix; `listTraces`, `getTrace` in Langfuse).
- **SDK / Local Fallback**: When MCP servers are absent, query via platform SDK or parse local trace files (`.evals/traces/*.json`).

### Step 2: Filter and Triage Anomaly Traces
Isolate traces flagged with:
- `status == "error"`
- Evaluation scores failing contract thresholds
- Step counts exceeding `budgets.max_step_ceiling`

### Step 3: Trajectory Sanitization & Minimization
1. **Redaction**: Strip credentials, authorization tokens, emails, and PII.
2. **Minimization**: Isolate the user input prompt, the sequence of tool invocations up to the failure point, and the mock tool responses.
3. **Precondition Extraction**: Map prior state and retrieved context into the test case format.

### Step 4: Emit Standardized Regression Fixture
Append new test cases into `.evals/datasets/regression_fixtures.jsonl` matching the Phase 3 schema:
- `category`: Categorized by failure type.
- `input`: Original prompt and extracted mock tool outputs.
- `expected_trajectory`: Corrected expected behavior according to `.evals/contract.yaml`.
- `metadata`: Source trace ID, timestamp, and failure reason.

### Step 5: Verify Reproduction
Run the mined fixture through Phase 2's `eval_engine.py` or Phase 4's `run_ci_eval.py` to confirm that the existing agent branch fails, establishing the test-driven regression baseline.

---

## 4. Bundled Mining Script (`scripts/mine_traces.py`)

```bash
uv run ~/.agents/skills/trace-feedback-miner/scripts/mine_traces.py \
  --source .evals/traces/runtime_traces.json \
  --contract .evals/contract.yaml \
  --output .evals/datasets/regression_fixtures.jsonl
```

---

## 5. Validation Gate

Before marking trace mining complete:
1. **Zero PII**: Verified that all API keys, session tokens, and personal data are scrubbed.
2. **Reproducibility**: The generated `.jsonl` record is fully self-contained with mock responses.
3. **Contract Alignment**: The new fixture references the correct `contract_id` and declared tool schemas.
