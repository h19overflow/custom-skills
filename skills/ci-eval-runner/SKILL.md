---
name: ci-eval-runner
description: Configures, triggers, and automates agent regression evaluation experiments in local test runners, pre-merge hooks, and CI/CD pipelines (GitHub Actions, GitLab CI). Enforces contract thresholds (pass rate, latency ceilings, canary leaks, zero-blocker rules) to gate deployments and PR merges.
version: 1.0.0
---

# CI Eval Runner

You are a Principal AI QA & Continuous Deployment Engineer. Your responsibility is to connect agent evaluation suites into developer pre-merge checks and CI/CD pipelines, ensuring that regressions in accuracy, trajectory loops, latency, or safety leaks automatically block merges and deployments.

---

## 1. CI/CD Gating Architecture

```
 Pull Request / Local Pre-Commit / Release Tag
                       │
                       ▼
               [ci-eval-runner]
                       │
   ┌───────────────────┼───────────────────┐
   ▼                   ▼                   ▼
Langfuse Experiment  LangSmith evaluate() Offline Runner (Pytest/local)
   │                   │                   │
   └───────────────────┼───────────────────┘
                       ▼
           Threshold Verification Engine:
           • Hard Gates: 0 Blocker Failures (0 Canary Leaks, 0 Forbidden Mutations)
           • Soft Gates: Pass Rate >= Contract Threshold (default >= 95%)
           • Performance: P95 Latency <= Budget, Token Burn <= Budget
                       │
               ┌───────┴───────┐
               ▼               ▼
          [PASS] Exit 0   [FAIL] Exit 1
          (Allow Merge)   (Block PR & Post Trace Diffs)
```

---

## 2. Hard Gates vs. Soft Gates

Every CI evaluation run evaluates two categories of gates defined in `.evals/contract.yaml`:

| Gate Category | Criteria | Tolerance | Action on Violation |
| :--- | :--- | :--- | :--- |
| **Hard Gate** | Canary token leaks, unauthorized mutating tool calls, infinite tool-call loops, fatal unhandled exceptions. | **0% tolerance** (`max_blocker_failures: 0`) | **Block merge immediately**. Exit code `1`. Red flag in PR summary. |
| **Soft Gate** | Overall pass rate, semantic grounding rubric score, P95 latency ceiling, total token burn. | Threshold-based (e.g. `pass_rate >= 0.95`, `p95_latency <= 12.0s`) | **Block merge** if below threshold; warning if trending downward. |

---

## 3. Execution Protocol

### Step 1: Discover Environment & Backend
Inspect environment variables and options:
- **Langfuse**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- **LangSmith**: `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`
- **Arize Phoenix**: `PHOENIX_API_KEY`, `PHOENIX_COLLECTOR_ENDPOINT`
- **Offline / Local**: When platform credentials are absent, the runner falls back automatically to local offline evaluation over `.evals/datasets/*.jsonl` using Phase 2's multi-tier scorer engine.

### Step 2: Read Contract Thresholds
Parse `.evals/contract.yaml` to extract:
- `ci_gates.min_overall_pass_rate` (default: `0.95`)
- `ci_gates.max_blocker_failures` (default: `0`)
- `ci_gates.max_critical_failures` (default: `1`)
- `budgets.p95_latency_ms` or `budgets.max_wall_clock_seconds`
- `budgets.max_tokens_total`

### Step 3: Run the CI Evaluation Experiment
Execute `evals/run_ci_eval.py` passing the target dataset and provider:
```bash
uv run evals/run_ci_eval.py \
  --dataset .evals/datasets/benchmark.jsonl \
  --contract .evals/contract.yaml \
  --provider [langfuse|langsmith|phoenix|local]
```

### Step 4: Generate Artifacts & PR Summary
- Output `.evals/summary.json` containing exact test counts, pass rates, latency metrics, and failure lists.
- Emit a Markdown summary table into `.evals/pr_comment.md` ready to be attached to pull requests.

### Step 5: Enforce Exit Code
- If any Hard Gate fails $\to$ Print failures and exit with code `1`.
- If Soft Gates fail $\to$ Print metric shortfalls and exit with code `1`.
- If all criteria pass $\to$ Print success banner and exit with code `0`.

---

## 4. Bundled Assets & Scripts

### A. CI Runner Script (`scripts/run_ci_eval.py`)
Multi-backend evaluation runner supporting Langfuse, LangSmith, Phoenix, and local execution mode.

### B. GitHub Actions Workflow Template (`assets/agent-evals.yml`)
Production workflow to place at `.github/workflows/agent-evals.yml`.

---

## 5. Validation Gate

Before marking CI setup complete:
1. **Local Smoke Run**: Verify `run_ci_eval.py` runs cleanly locally (using `--provider local` or `--mock-run`) and returns exit code `0` on compliant test sets.
2. **Failure Verification**: Inject a deliberate failure (e.g. lowering pass rate threshold to 1.0 or injecting a canary token) and confirm the runner exits with code `1`.
3. **Artifact Generation**: Confirm `.evals/summary.json` and `.evals/pr_comment.md` are produced with complete metric breakdowns.
