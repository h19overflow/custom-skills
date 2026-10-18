---
name: dataset-benchmark-builder
description: Constructs, generates, and synchronizes layered golden evaluation datasets, adversarial test cases, tool-recovery fixtures, and RAG distraction benchmarks into local versioned JSONL files and hosted platforms (Langfuse, LangSmith, Arize Phoenix). Use whenever generating benchmark suites, synthesizing test fixtures from contracts, or publishing datasets to evaluation backends.
version: 1.0.0
---

# Dataset Benchmark Builder

You are a Principal AI Evaluation Dataset Architect. Your responsibility is to curate, synthesize, and synchronize high-coverage benchmark datasets derived directly from `.evals/contract.yaml` (Phase 1) and evaluated by Phase 2 scorers.

---

## 1. The 4-Tier Benchmark Suite Architecture

Agent evaluation datasets cannot be static `(input, expected_text)` pairs. They must contain stateful assertions, tool-call expectations, mocked environment fixtures, and negative poison pills across four slices:

```
┌────────────────────────────────────────────────────────────────────────┐
│ SLICE 1: Golden Trajectories                                          │
│   • Purpose: Validate baseline happy paths and optimal tool execution │
│   • Elements: Clean user intent, ideal tool DAG sequence, minimal      │
│     step count, exact state mutation outcomes.                         │
├────────────────────────────────────────────────────────────────────────┤
│ SLICE 2: Adversarial & Edge Cases                                     │
│   • Purpose: Enforce alignment, guardrails, and boundary safety       │
│   • Elements: Prompt injection attempts, canary token extraction,     │
│     conflicting instructions, missing required input fields.           │
├────────────────────────────────────────────────────────────────────────┤
│ SLICE 3: Tool Error & Degradation                                     │
│   • Purpose: Validate error recovery, retries, and fallback branches   │
│   • Elements: Mocked HTTP 429 rate limits, 500 server errors, malformed│
│     tool payloads, missing DB entities, unexpected timeouts.           │
├────────────────────────────────────────────────────────────────────────┤
│ SLICE 4: RAG Needle & Distraction                                     │
│   • Purpose: Test context faithfulness and resistance to distractors  │
│   • Elements: Contradictory context chunks, distractor filler text,    │
│     unsubstantiated claims, outdated policy needles.                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Benchmark Record Schema

Every test case in `.evals/datasets/*.jsonl` must conform to this schema:

```json
{
  "id": "tc_order_refund_001",
  "category": "golden", // golden | adversarial | tool_failure | rag_distraction
  "input": {
    "task": "Process full refund for defective headphones on order ord_12345678",
    "customer_id": "cust_87654321",
    "context": {
      "channel": "chat",
      "user_tier": "premium"
    },
    "mock_tool_responses": {
      "lookup_customer": {
        "id": "cust_87654321",
        "status": "active",
        "tier": "premium"
      }
    }
  },
  "expected_trajectory": {
    "required_tools": ["lookup_customer", "calculate_refund", "execute_refund"],
    "forbidden_tools": ["execute_raw_sql", "delete_account"],
    "tool_argument_constraints": {
      "execute_refund": {
        "order_id": "ord_12345678",
        "reason": "Defective item"
      }
    },
    "max_steps": 5,
    "expected_final_state": {
      "resolution_status": "resolved",
      "mutations_committed": ["execute_refund"]
    }
  },
  "retrieved_chunks": [
    "Policy Chunk A: Orders within 30 days are eligible for immediate full refund."
  ],
  "metadata": {
    "difficulty": "medium", // easy | medium | hard | stress
    "layer": "agent_trajectory", // prompt | rag | agent_trajectory | multi_agent
    "contract_version": "1.0.0",
    "created_at": "2026-10-03"
  }
}
```

---

## 3. Execution Protocol

### Step 1: Ingest Contract Invariants
Read `.evals/contract.yaml`:
- Identify all declared tools in `tool_contracts` and allowed paths in `trajectory_policy`.
- Extract canary tokens and banned patterns from `behavioral_profile`.
- Extract declared error recovery paths (e.g. `on_decline: "escalate_to_human"`).

### Step 2: Synthesize Benchmark Slices (Minimum 10–20 Items)
Construct diverse test cases balanced across the 4 slices:
1. **Golden (40%)**: Standard workflows satisfying all preconditions.
2. **Adversarial (20%)**: Jailbreak prompts, attempts to trigger unauthorized mutations without preconditions, canary token extraction prompts.
3. **Tool Failure (20%)**: Mock tool responses returning errors (e.g. 500 error from `calculate_refund`) asserting the agent invokes the recovery tool.
4. **RAG Distraction (20%)**: Injected contradictory chunks asserting the agent rejects fabricated context.

### Step 3: Persist Local Versioned Files
- Write records to `.evals/datasets/<dataset_name>.jsonl`.
- Write environment mock fixtures to `.evals/fixtures/<dataset_name>_fixtures.json`.

### Step 4: Synchronize to Hosted Platform
Run the synchronization script or execute MCP tools:
- **Langfuse**: Upsert dataset and dataset items with input, expected output, and metadata.
- **LangSmith**: Register dataset and create examples with dataset ID association.
- **Arize Phoenix**: Upload dataset dataframe with input/output key mapping.

---

## 4. Bundled Automation Scripts

### Script A: Seed Generator (`scripts/generate_seed_dataset.py`)
Generates a compliant 4-slice seed benchmark directly from `.evals/contract.yaml`:
```bash
uv run ~/.agents/skills/dataset-benchmark-builder/scripts/generate_seed_dataset.py \
  --contract .evals/contract.yaml \
  --output .evals/datasets/agent_benchmark.jsonl
```

### Script B: Idempotent Remote Sync (`scripts/sync_datasets.py`)
Idempotently publishes the dataset to Langfuse, LangSmith, or Phoenix:
```bash
uv run ~/.agents/skills/dataset-benchmark-builder/scripts/sync_datasets.py \
  --file .evals/datasets/agent_benchmark.jsonl \
  --name "agent-order-management-v1" \
  --provider langfuse \
  --dry-run
```

---

## 5. Validation Gate

Before concluding dataset construction:
1. **Schema Conformity**: Every item in `.jsonl` validates against the Benchmark Item Schema.
2. **Slice Balance**: Ensure all 4 categories (`golden`, `adversarial`, `tool_failure`, `rag_distraction`) are represented.
3. **Deterministic Expectations**: Every item defines concrete `required_tools` and `max_steps`.
4. **Zero Flakiness**: Mock fixtures are fully deterministic and require no external live network services.
