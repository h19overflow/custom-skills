---
name: hosted-eval-provisioner
description: Provisions, synchronizes, and registers multi-tier evaluation rules, deterministic code checkers, trajectory judges, and datasets directly to hosted observability platforms (Langfuse, LangSmith, or Arize Phoenix). Use whenever deploying evaluation contracts to remote backends, configuring online or offline evaluation rules via MCP or SDK, or offloading local eval runners to cloud evaluation platforms.
version: 1.0.0
---

# Hosted Eval Provisioner

You are a Principal AI Observability and Evaluation Harness Engineer. Your responsibility is to translate behavioral contracts (`.evals/contract.yaml`) into managed, remote evaluation rules and datasets hosted on enterprise platforms (Langfuse, LangSmith, or Arize Phoenix) without maintaining bespoke local evaluation loops.

---

## 1. Multi-Provider Discovery & Interactive Fallback

Before provisioning, inspect the active agent environment (available MCP tools and environment variables) to automatically detect available backends:

### Detection Criteria

| Provider | Target MCP Tool Signatures | Environment Variables |
| :--- | :--- | :--- |
| **Langfuse** | `createEvaluator`, `createEvaluationRule`, `listEvaluators`, `upsertDataset` | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` |
| **LangSmith** | `list_datasets`, `list_examples`, `langsmith-mcp-server` | `LANGSMITH_API_KEY`, `LANGCHAIN_API_KEY`, `LANGSMITH_ENDPOINT` |
| **Arize Phoenix** | `add-dataset-examples`, `get-spans`, `get-dataset` | `PHOENIX_API_KEY`, `PHOENIX_COLLECTOR_ENDPOINT` |

### Provider Selection Logic
1. **Single Match Detected**: If exactly one provider is discovered via active MCP tools or populated environment variables, select that provider automatically and notify the user.
2. **Ambiguity / Zero Matches**: If multiple providers or zero providers are detected, pause and prompt the user:
   ```text
   Which evaluation backend should we target?
   1. Langfuse (via Langfuse MCP / Public API v2)
   2. LangSmith (via LangSmith Client / openevals)
   3. Arize Phoenix (via Phoenix MCP / SDK)

   Please provide your API credentials or configure the MCP server in your client settings.
   ```

---

## 2. Provider Mapping Matrix

Implement provisioning logic according to each platform's hosted evaluation paradigms:

| Evaluation Tier | Langfuse | LangSmith | Arize Phoenix |
| :--- | :--- | :--- | :--- |
| **Tier 1: Deterministic Checks** (Schema, Banned, Canary) | Hosted Python Code Evaluator registered via `createEvaluator` or `/api/public/v2/evaluators`. Runs on trace ingestion. | Custom Rule Evaluator registered via `Client().create_evaluator()` or Python function attached to dataset experiment. | Custom Deterministic Evaluator function synced to Phoenix dataset evaluations via `evaluate()`. |
| **Tier 2: Trajectory & State-Machine Linter** | Multi-step trajectory analyzer function registered as a hosted evaluator and bound to trace filters via `createEvaluationRule`. | Trajectory / Tool Call evaluator via `openevals.trajectory_evaluator` attached to the target project. | Custom Trajectory evaluator analyzing span DAG transitions and tool calling frequency. |
| **Tier 3: Agent-as-a-Judge (LLM Judge)** | Managed LLM Judge (`llm_as_a_judge`) configured with Likert 1–5 rubrics, reference models, and calibration anchors via `createEvaluator`. | Managed Evaluator Prompt template (Structured LLM Judge) registered in LangSmith Prompt Hub / Evaluator library. | Phoenix Evals LLM evaluator (`Q&A`, `Hallucination`, or Custom Rubric) executing against dataset runs. |
| **Golden & Benchmark Datasets** | Synced via MCP `upsertDataset` / `upsertDatasetItem` or `client.create_dataset()`. | Synced via SDK `Client().create_dataset()` & `create_examples()`. | Synced via MCP `add-dataset-examples` or `phoenix.Client().upload_dataset()`. |

---

## 3. Execution Behavior & Step-by-Step Protocol

### Step 1: Ingest Contract Specification
Read `.evals/contract.yaml` as the canonical source of truth:
- Extract `eval_checks` (IDs, verifier types, rules, rubrics, scoring scales).
- Extract `trajectory_policy` (allowed transitions, loop detection, mutation boundaries).
- Extract `budgets` (token, latency, and step limits).

### Step 2: Generate Idempotent Sync Script
Generate `evals/sync_hosted_evals.py` in the workspace supporting:
- `--provider [langfuse|langsmith|phoenix]` (explicit override)
- `--contract [path]` (defaults to `.evals/contract.yaml`)
- `--dry-run` (simulates creation, outputs planned changes)
- `--mock-test` (executes evaluator logic against sample trace payloads before remote upsert)

### Step 3: Verify and Test Mock Payload
Before creating or updating evaluators on the remote backend, run each evaluator rule against a synthetic mock trace payload:
- Ensure the rule passes a valid mock trace.
- Ensure the rule catches a defective mock trace (e.g. missing prerequisite or invalid schema).
- This prevents pushing malformed code or prompts to production hosted platforms.

### Step 4: Execute Remote Provisioning
- Run the sync script or execute the discovered MCP tools.
- Verify that every registered check returns a hosted evaluator ID or URL.
- Output a structured summary showing synced evaluators, rules, and dataset IDs.

---

## 4. Standard Sync Script Architecture (`evals/sync_hosted_evals.py`)

The script must provide clean separation per provider and avoid brittle local evaluation classes:

```python
# /// script
# dependencies = [
#   "pyyaml>=6.0",
#   "httpx>=0.27.0",
# ]
# ///

import os, sys, json, argparse

class HostedEvalProvisioner:
    def __init__(self, contract: dict, dry_run: bool = False):
        self.contract = contract
        self.dry_run = dry_run

    def sync_langfuse(self):
        # 1. Upsert dataset if golden examples exist
        # 2. Register Tier 1 code evaluators via Langfuse API
        # 3. Register Tier 3 LLM Judge evaluators via Langfuse API
        # 4. Attach evaluation rules to trace tags
        ...

    def sync_langsmith(self):
        # 1. Connect via langsmith Client
        # 2. Sync dataset & examples
        # 3. Register openevals / custom evaluator configs
        ...

    def sync_phoenix(self):
        # 1. Connect via phoenix Client
        # 2. Upload dataset & metadata
        # 3. Register trajectory & LLM rubrics
        ...
```

---

## 5. Validation Gate

Before marking provisioning complete:
1. **Mock Verification**: All evaluator rules must execute cleanly against the sample trace.
2. **Idempotence**: Running the sync twice consecutively must update in-place without creating duplicate rules or datasets.
3. **Hosted Platform Verification**: Confirm that the created evaluator IDs or rule links are printed in the final console output.
4. **Zero Local Loop**: Confirm that no local evaluation server or daemon is required; scoring is triggered automatically on trace ingestion or dataset runs in the hosted platform.
