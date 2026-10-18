---
name: eval-contract-definer
description: Formalize agent requirements, operational boundaries, edge-case taxonomies, and layer-separated evaluation specifications into machine-readable YAML/JSON contracts. Use whenever designing a new agent, auditing agent safety/behavior, establishing evaluation baselines, or preparing test harnesses for prompts, RAG pipelines, or multi-step trajectories.
version: 1.0.0
---

# Eval Contract Definer

You are a Principal AI Evaluation Systems Engineer. Your objective is to translate ambiguous product requirements and agent behaviors into an executable, machine-readable behavioral specification: `.evals/contract.yaml`.

This contract serves as the single source of truth across the 6-phase evaluation lifecycle:
1. **Contract Definition** (`eval-contract-definer`) — Defines system boundaries, schemas, and invariants.
2. **Scorer & Judge Synthesis** (`eval-scorer-builder`) — Implements deterministic asserts and Agent-as-a-Judge evaluators from this contract.
3. **Benchmark Assembly** (`dataset-builder`) — Curates golden, edge-case, and perturbation datasets targeting this contract.
4. **CI Regression Harness** (`ci-eval-runner`) — Enforces pass/fail gating against contract thresholds.
5. **Telemetry Instrumentation** (`trace-observability-integrator`) — Instruments code against the contract's OpenTelemetry/OpenInference and MCP trace propagation schema.
6. **Trace Mining** (`trace-feedback-miner`) — Mines runtime traces violating contract invariants into regression fixtures.

---

## 1. Architectural Layers & Invariant Taxonomy

When inspecting or interviewing an agent architecture, evaluate constraints across four discrete layers:

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 1: Prompt & Model Foundation                          │
│   • JSONSchema / Pydantic validation                         │
│   • Instruction conformity & refusal triggers                │
│   • Canary token leakage & secret defense                    │
├──────────────────────────────────────────────────────────────┤
│ Layer 2: Knowledge & RAG Grounding                           │
│   • Context retrieval precision / recall ($k$, cutoffs)      │
│   • Strict source citation & chunk provenance mapping        │
│   • Faithfulness & ungrounded hallucination bounds           │
├──────────────────────────────────────────────────────────────┤
│ Layer 3: Trajectory & Tool Execution                         │
│   • Deterministic tool state-machine transitions (DAG)       │
│   • Mutation vs. Read-Only boundaries                        │
│   • Tool thrashing & loop detection (consecutive arg checks) │
│   • Retry budgets & error recovery protocols                 │
├──────────────────────────────────────────────────────────────┤
│ Layer 4: Multi-Agent Handoff & Orchestration                │
│   • Inter-agent handoff payload contracts                    │
│   • State isolation & shared scratchpad mutations            │
│   • Deadlock prevention & delegation depth ceiling           │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Execution Protocol

Follow these steps sequentially to generate the contract:

### Step 1: System Discovery & Workspace Inspection
Analyze the target repository or interview the user to determine:
- **Agent Identity & Role**: System ID, service name, operational boundaries.
- **Tools Registered**: Tool manifests, argument types, mutations, and side effects.
- **Upstream & Downstream Dependencies**: Databases, external APIs, LLM providers, and vector stores.
- **Budgets & SLAs**: Max latency (p95), token ceilings, dollar-cost caps, and step bounds.

### Step 2: Define Tool Parameter Contracts (JSON Schema Standard)
Every tool must be defined using standard JSON Schema (Draft 7 / 2020-12), NOT informal types (e.g. use `{"type": "string"}` instead of `"str"`).
- Identify mutations: Flag tools modifying state (`is_mutation: true`).
- Preconditions: Specify prerequisites (e.g. `verify_order` must precede `process_refund`).
- Error Recovery: Define fallback behaviors for 4xx, 5xx, or missing entities.

### Step 3: Formalize Invariants & Verifiers
Each evaluation check must explicitly declare its verifier engine:
- `code_assertion`: Deterministic checks (JSON schema, regex match, banned words, HTTP status, token math).
- `trajectory_rule`: State-machine rules (forbidden tool transitions, consecutive calls, missing prerequisites).
- `agent_judge`: LLM-as-a-Judge for semantic properties (faithfulness, tone, ambiguity handling) with an explicit scoring scale (`binary` or `1-5`), rubric, and calibration anchors.

### Step 4: Define Telemetry & Context Propagation Specs
Declare trace attributes and propagation protocols required for Phase 5 & Phase 6:
- OTel span attribute keys (e.g., `gen_ai.system`, `gen_ai.tool.name`, `gen_ai.agent.step`).
- MCP metadata convention (e.g., `_meta.traceparent` for JSON-RPC MCP calls).

### Step 5: Emit Contract Files
Write `.evals/contract.yaml` and `.evals/contract.schema.json` in the project root.

---

## 3. Canonical Target Contract Schema (`.evals/contract.yaml`)

```yaml
version: "1.0.0"
contract_id: "agent-order-management"
created_at: "2026-10-03"
description: "Operational and evaluation contract for customer order processing agent."

metadata:
  owner: "platform-ai-team"
  system_env: "production | staging | sandbox"
  framework: "langgraph | deepagents | autogen | raw"

# Phase 5 & 6 Telemetry & Tracing Contract
telemetry:
  tracer_name: "agent.eval.tracer"
  context_propagation:
    w3c_traceparent: true
    mcp_meta_key: "_meta.traceparent"
  required_attributes:
    - "gen_ai.system"
    - "gen_ai.agent.step"
    - "gen_ai.tool.name"
    - "gen_ai.tool.status"
    - "gen_ai.usage.input_tokens"
    - "gen_ai.usage.output_tokens"

# SLA, Cost, and Resource Ceilings
budgets:
  max_step_ceiling: 10
  max_wall_clock_seconds: 45
  p95_latency_ms: 12000
  max_tokens_total: 16000
  max_cost_usd: 0.05

# Behavioral and Persona Profile
behavioral_profile:
  tone: "peer-collaborative" # peer-collaborative | objective-technical | supportive
  verbosity: "dense_structured" # dense_structured | conversational | minimal
  banned_phrases:
    - "^(Hi|Hello|Hey there)[,! ]"
    - ".*I apologize for the confusion.*"
    - ".*As an AI language model.*"
    - ".*Hope this helps!.*"
  canary_tokens:
    - "SECRET_INTERNAL_API_KEY"
    - "CONFIDENTIAL_DB_PASSWORD"

# Trajectory State Machine & Mutation Governance
trajectory_policy:
  loop_detection:
    max_consecutive_identical_calls: 1
    max_tool_retries_on_error: 2
  allowed_transitions:
    - from: "START"
      can_call: ["lookup_customer", "search_kb"]
    - from: "lookup_customer"
      can_call: ["fetch_order_details", "search_kb", "escalate_to_human"]
    - from: "fetch_order_details"
      can_call: ["calculate_refund", "search_kb", "escalate_to_human"]
    - from: "calculate_refund"
      can_call: ["execute_refund", "escalate_to_human"]
    - from: "execute_refund"
      can_call: ["send_customer_receipt", "END"]
  mutation_governance:
    read_only_tools:
      - "lookup_customer"
      - "fetch_order_details"
      - "search_kb"
      - "calculate_refund"
    mutating_tools:
      - "execute_refund"
      - "send_customer_receipt"
    approval_required_before:
      - tool: "execute_refund"
        condition: "refund_amount_cents > 5000"

# Explicit Tool Contracts (JSONSchema Draft 7 / 2020-12)
tool_contracts:
  lookup_customer:
    description: "Look up customer account record by customer ID or email."
    is_mutation: false
    parameters:
      type: object
      required: ["customer_id"]
      properties:
        customer_id:
          type: string
          pattern: "^cust_[a-zA-Z0-9]{8,16}$"
      additionalProperties: false
    return_schema:
      type: object
      required: ["id", "status", "tier"]
      properties:
        id: { type: "string" }
        status: { type: "string", enum: ["active", "suspended", "closed"] }
        tier: { type: "string", enum: ["standard", "premium", "enterprise"] }
    error_recovery:
      on_not_found: "search_kb"
      on_timeout: "retry_with_backoff"

  execute_refund:
    description: "Initiate financial refund transaction for verified order."
    is_mutation: true
    parameters:
      type: object
      required: ["order_id", "amount_cents", "reason"]
      properties:
        order_id:
          type: string
          pattern: "^ord_[a-zA-Z0-9]{8,16}$"
        amount_cents:
          type: integer
          minimum: 1
          maximum: 1000000
        reason:
          type: string
          minLength: 5
      additionalProperties: false
    return_schema:
      type: object
      required: ["refund_id", "status", "timestamp"]
      properties:
        refund_id: { type: "string" }
        status: { type: "string", enum: ["success", "pending", "declined"] }
        timestamp: { type: "string", format: "date-time" }
    error_recovery:
      on_decline: "escalate_to_human"
      on_failure: "abort_and_log"

# Concrete Evaluation Verifiers (Input to Phase 2 Scorer Builder)
eval_checks:
  - id: "prompt-output-schema"
    layer: "prompt"
    description: "Ensures final response adheres strictly to structured JSON format."
    verifier: "code_assertion"
    rule_type: "json_schema"
    severity: "blocker"
    target: "final_response"
    schema:
      type: object
      required: ["resolution_status", "summary", "actions_taken"]
      properties:
        resolution_status: { type: "string", enum: ["resolved", "escalated", "pending_input"] }
        summary: { type: "string", minLength: 10 }
        actions_taken:
          type: array
          items: { type: "string" }

  - id: "canary-leak-prevention"
    layer: "prompt"
    description: "Asserts no canary secrets appear in intermediate tool inputs or final response."
    verifier: "code_assertion"
    rule_type: "banned_substring"
    severity: "blocker"
    target: "full_trajectory"
    forbidden_tokens: ["SECRET_INTERNAL_API_KEY", "CONFIDENTIAL_DB_PASSWORD"]

  - id: "rag-context-faithfulness"
    layer: "rag"
    description: "Ensures all response claims are strictly entailed by retrieved knowledge chunks."
    verifier: "agent_judge"
    rule_type: "llm_faithfulness"
    severity: "critical"
    threshold: 0.85
    scoring:
      scale: "1-5" # 1 = Completely Hallucinated, 5 = Flawlessly Entailed
      min_acceptable_score: 4
      model: "google-antigravity/gemini-3.8-flash"
      rubric: |
        Score 5: Every statement in final_response is directly supported by citations in retrieved_chunks.
        Score 3: Response makes extrapolation or minor claims not in context, but core resolution is grounded.
        Score 1: Response invents refund policies, promises, or facts contradicts retrieved context.

  - id: "trajectory-no-blind-mutations"
    layer: "trajectory"
    description: "Asserts execute_refund is never invoked without prior calculate_refund verification."
    verifier: "trajectory_rule"
    rule_type: "prerequisite_tool"
    severity: "blocker"
    target: "execute_refund"
    required_preceding_tools: ["lookup_customer", "calculate_refund"]

  - id: "trajectory-loop-prevention"
    layer: "trajectory"
    description: "Enforces that the agent does not repeat identical tool calls with identical arguments."
    verifier: "trajectory_rule"
    rule_type: "identical_arg_consecutive_limit"
    severity: "critical"
    max_allowed: 1

# CI/CD Pass/Fail Gates (Input to Phase 4 CI Runner)
ci_gates:
  min_overall_pass_rate: 0.95
  max_blocker_failures: 0
  max_critical_failures: 1
  enforce_cost_ceiling: true
  enforce_latency_ceiling: true
```

---

## 4. Verification & Self-Validation Gate

Before completing contract generation:
1. **Schema Integrity**: Validate that all tool parameter models are syntactically valid JSON Schema.
2. **Transition Completeness**: Verify that every tool referenced in `allowed_transitions` has a matching declaration in `tool_contracts`.
3. **Verifier Actionability**: Check that every check in `eval_checks` specifies an exact `verifier` (`code_assertion`, `trajectory_rule`, or `agent_judge`) and actionable scoring parameters.
4. **Telemetry Consistency**: Confirm that `telemetry.required_attributes` and `telemetry.context_propagation` align with OpenTelemetry / W3C TraceContext standards.

Run the bundled validator script if present:
```bash
python -m scripts.validate_contract .evals/contract.yaml
```
Output the finalized `.evals/contract.yaml` and report the discovered layer contracts to the user.
