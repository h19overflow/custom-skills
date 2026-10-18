# Architectural Topologies, Alignment Constraints & Substrate Mappings

A practical reference guide for composing patterns from *The AI Agent Engineer's Guide: 60 Patterns for Building Autonomous Systems* into robust, production-grade workflows.

---

## 1. Multi-Pattern Composition Topologies

In production, agents rarely operate in isolation. They combine into defined multi-pattern topologies depending on the task's complexity, risk profile, and latency constraints.

### Topology A: The Staged Sequential Pipeline (Typed Assembly Line)
*Use when tasks decompose into deterministic phases where output from phase $N$ strictly serves as typed input to phase $N+1$.*

```text
[Input Percept]
      │
      ▼
┌─────────────────────────────────┐
│ Agent 2: Document Layout        │ (Perception: typed AST / chunk tree)
└───────────────┬─────────────────┘
                │ Typed DocumentTree
                ▼
┌─────────────────────────────────┐
│ Agent 7: Schema-Inference       │ (Perception/Reasoning: calibrated field schemas)
└───────────────┬─────────────────┘
                │ Target Pydantic Schema
                ▼
┌─────────────────────────────────┐
│ Agent 41: Pipeline Orchestrator │ (Coordination: stage runner with typed handoffs)
└───────────────┬─────────────────┘
                │
                ├────────────────────────────────────────┐
                ▼                                        ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│ Agent 55: Provenance Tracker    │    │ Agent 53: Constitution-Bound    │
│ (Attaches hashes & char offsets)│    │ (Pre-release policy assertion)  │
└───────────────┬─────────────────┘    └────────────────┬────────────────┘
                │                                        │
                └───────────────────┬────────────────────┘
                                    ▼
                          [Verified Output Schema]
```

**Key Invariant**: Every inter-stage handoff must be validated via a Pydantic contract. If stage $K$ outputs invalid JSON or missing required fields, stage $K$ retries or fails closed before stage $K+1$ executes.

---

### Topology B: The Supervisory Fan-Out (Supervisor-Worker Pool)
*Use for embarrassingly parallelizable or domain-specialized subtasks (e.g., analyzing 20 chapters of a book, reviewing 50 source files, or crawling 15 endpoints).*

```text
                    ┌──────────────────────────────┐
                    │ Agent 16: Hierarchical       │
                    │ Decomposer                   │
                    └──────────────┬───────────────┘
                                   │ Goal Tree
                                   ▼
                    ┌──────────────────────────────┐
                    │ Agent 45: Supervisor-Worker  │
                    │ Controller                   │
                    └──────────────┬───────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼ Task Slice 1            ▼ Task Slice 2            ▼ Task Slice N
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Worker Agent    │       │ Worker Agent    │       │ Worker Agent    │
│ + Agent 30:     │       │ + Agent 30:     │       │ + Agent 30:     │
│   Tool Selector │       │   Tool Selector │       │   Tool Selector │
│ + Agent 32:     │       │ + Agent 32:     │       │ + Agent 32:     │
│   Sandbox       │       │   Sandbox       │       │   Sandbox       │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │ Partial Outputs
                                   ▼
                    ┌──────────────────────────────┐
                    │ Agent 40: Consensus-Builder  │
                    │ Aggregator                   │
                    └──────────────┬───────────────┘
                                   │ Merged State
                                   ▼
                    ┌──────────────────────────────┐
                    │ Agent 37: Side-Effect        │
                    │ Auditor (2-Phase Commit)     │
                    └──────────────────────────────┘
```

**Operational Properties**:
- Supervisor dynamically adjusts batch concurrency based on API rate limits.
- Isolated workers run in ephemeral sandboxes (Agent 32) to prevent shared state contamination.
- Consensus Builder (Agent 40) merges partial outputs while preserving identified contradictions.

---

### Topology C: Adversarial Multi-Agent Debate & Adjudication
*Use when evaluating high-stakes, contestable decisions without single ground truth (e.g., credit committee, medical diagnostic ambiguity, M&A risk).*

```text
                      [Contested Hypothesis]
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼ Stance: Pro                                   ▼ Stance: Con
┌───────────────────────────────┐       ┌───────────────────────────────┐
│ Reasoner A (Bull / Affirmative)│       │ Reasoner B (Bear / Negative)  │
│ + Agent 14: Belief Updater    │       │ + Agent 9: Counterfactual     │
└───────────────┬───────────────┘       └───────────────┬───────────────┘
                │ Turn 1 Arg                    │ Turn 1 Arg
                └───────────────┬───────────────┘
                                ▼
                ┌───────────────────────────────┐
                │ Agent 39: Debate Moderator    │
                │ (Evaluates claims on merits,  │
                │ detects fake debate / loops)  │
                └───────────────┬───────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │ Agent 15: Self-Consistency    │
                │ Voter / Adjudicator           │
                └───────────────┬───────────────┘
                                │ Verdict + Disagreements
                                ▼
                ┌───────────────────────────────┐
                │ Agent 42: HITL Liaison        │
                │ (If winner=null or low margin)│
                └───────────────────────────────┘
```

---

### Topology D: The Deliberative Reflection & Verification Loop
*Use when generating artifacts requiring formal correctness (code generation, SQL synthesis, mathematical proofs, structured extraction).*

```text
             ┌───────────────────────────────────────────┐
             │ Agent 19: Plan-Then-Execute (Initial Plan)│
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
         ┌────────────────────────────────────────────────────────┐
         │ Generator Step (e.g., Agent 35: DB Query Synthesizer)  │◄─────────┐
         └─────────────────────────┬──────────────────────────────┘          │
                                   │ Candidate Query                         │
                                   ▼                                         │
         ┌────────────────────────────────────────────────────────┐          │
         │ Agent 8: Chain-of-Thought Auditor                      │          │
         │ - Syntactic AST validation                             │          │
         │ - Schema integrity check                               │          │
         │ - Mutation / injection scan                            │          │
         └─────────────────────────┬──────────────────────────────┘          │
                                   │                                         │
                         Pass? ────┴─── No (Critique & Diagnostics)          │
                           │                          │                      │
                          Yes                         ▼                      │
                           │       ┌──────────────────────────────────────┐  │
                           │       │ Agent 47: Reflection Agent           │──┘
                           │       │ (Revises draft incorporating audit)  │
                           │       └──────────────────────────────────────┘
                           ▼
         ┌────────────────────────────────────────────────────────┐
         │ Agent 37: Side-Effect Auditor (Safe Execution & Rollback)
         └────────────────────────────────────────────────────────┘
```

---

### Topology E: The Human-in-the-Loop Escalation Escort
*Use in safety-critical systems where irreversible decisions must be gated by human operators.*

```text
[Incoming Intent]
       │
       ▼
┌──────────────────────────────┐
│ Agent 54: Refusal-Calibrator │ ── Reject ──► [Graceful Rejection]
└──────────────┬───────────────┘
               │ Allowed
               ▼
┌──────────────────────────────┐
│ Agent 53: Constitution-Bound │ ── Policy Violation ──► [Halt & Audit]
└──────────────┬───────────────┘
               │ Compliant
               ▼
┌──────────────────────────────┐
│ Autonomous Execution Plan    │
└──────────────┬───────────────┘
               │
               ▼
    Confidence Threshold < τ OR High-Stakes Side Effect?
               │
       ┌───────┴───────┐
      Yes              No
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ Agent 42:    │ │ Agent 37:    │
│ HITL Liaison │ │ Side-Effect  │
│ (Presents    │ │ Execution    │
│ Decision Card│ └──────────────┘
│ + Pauses)    │
└──────┬───────┘
       │ Approved?
   ┌───┴───┐
  Yes      No
   │       │
   ▼       ▼
[Execute] [Abort / Rollback (Agent 60)]
```

---

## 2. Domain Alignment Constraints Matrix

Every production domain imposes strict legal and risk boundaries. The following matrix prescribes the **mandatory, non-negotiable patterns** required for each domain:

| Domain | Key Regulations | Risk Horizon | Mandatory Alignment Patterns | Recommended Core Patterns |
| :--- | :--- | :--- | :--- | :--- |
| **Healthcare / Clinical Decision Support** | HIPAA, HITECH, FDA SaMD | Years / Life-impacting | **Agent 57 (Privacy-Preserving)**<br>**Agent 55 (Provenance Tracker)**<br>**Agent 42 (HITL Liaison)**<br>**Agent 58 (Explainer)** | Agent 2 (Doc Layout)<br>Agent 14 (Belief Updater)<br>Agent 40 (Consensus-Builder) |
| **Financial Services & Underwriting** | SOX, FCRA, SEC Rule 17a-4, Basel III | Multi-million dollar / Years | **Agent 55 (Provenance Tracker)**<br>**Agent 37 (Side-Effect Auditor)**<br>**Agent 53 (Constitution-Bound)**<br>**Agent 59 (Drift-Detector)** | Agent 11 (Constraint-Sat)<br>Agent 35 (DB Query)<br>Agent 39 (Debate Moderator) |
| **Legal & Regulatory Compliance** | ABA Rules, GDPR, Confidentiality | Years / High liability | **Agent 55 (Provenance Tracker)**<br>**Agent 53 (Constitution-Bound)**<br>**Agent 29 (Persistent Identity w/ Erasure)**<br>**Agent 54 (Refusal-Calibrator)** | Agent 2 (Doc Layout)<br>Agent 16 (Hierarchical Decomp)<br>Agent 8 (CoT Auditor) |
| **Autonomous Code Engineering & DevOps** | SOC2, ISO 27001, Least Privilege | Minutes to hours (Revertible) | **Agent 32 (Code Sandbox)**<br>**Agent 33 (Shell Operator)**<br>**Agent 37 (Side-Effect Auditor)**<br>**Agent 60 (Off-Switch)** | Agent 17 (ReAct Loop)<br>Agent 19 (Plan-Then-Execute)<br>Agent 47 (Reflection) |
| **Public-Facing Customer Service** | GDPR, CCPA, COPPA | Reputational / Regulatory fines | **Agent 57 (Privacy-Preserving)**<br>**Agent 54 (Refusal-Calibrator)**<br>**Agent 29 (Persistent Identity)**<br>**Agent 46 (Feedback Loop)** | Agent 38 (Dispatcher)<br>Agent 23 (Episodic Buffer)<br>Agent 42 (HITL Liaison) |

---

## 3. Substrate-Agnostic Implementation Blueprint

Patterns can be mapped directly into popular orchestrators and Python runtimes without vendor lock-in.

### A. StateGraph Mapping (LangGraph / Asyncio State Machines)

```python
from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field

# 1. State Definition (Context & Memory)
class AgentState(TypedDict):
    input_text: str
    target_schema: dict | None
    plan: list[str]
    current_step: int
    draft_output: dict | None
    audit_passed: bool
    provenance_hashes: list[str]
    human_approved: bool | None

# 2. Node Functions (Load-bearing Pattern Execution)
def plan_node(state: AgentState) -> dict:
    # Pattern 16: Hierarchical Decomposer / Pattern 19: Plan-Then-Execute
    ...
    return {"plan": ["step1", "step2"], "current_step": 0}

def execute_step_node(state: AgentState) -> dict:
    # Pattern 17: ReAct / Pattern 30: Tool Selector
    ...
    return {"draft_output": {"data": 123}, "provenance_hashes": ["sha256_abc"]}

def auditor_node(state: AgentState) -> dict:
    # Pattern 8: CoT Auditor + Pattern 53: Constitution-Bound + Pattern 55: Provenance Tracker
    valid_hashes = verify_provenance(state["draft_output"], state["provenance_hashes"])
    policy_ok = check_constitution(state["draft_output"])
    return {"audit_passed": valid_hashes and policy_ok}

def reflection_node(state: AgentState) -> dict:
    # Pattern 47: Reflection Agent
    ...
    return {"current_step": state["current_step"]}

def hitl_gate(state: AgentState) -> Literal["proceed", "escalate"]:
    # Pattern 42: HITL Liaison
    if not state["audit_passed"]:
        return "escalate"
    return "proceed"
```

### B. Fail-Closed Provenance Pointer Contract (Pydantic V2)

```python
from pydantic import BaseModel, Field, field_validator
import hashlib

class ProvenancePointer(BaseModel):
    source_uri: str
    doc_hash: str = Field(description="SHA-256 hash of the exact source document artifact")
    start_char: int
    end_char: int
    verbatim_text: str

    @field_validator("doc_hash")
    def validate_hash_format(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("Invalid SHA-256 hash format for provenance tracking")
        return v.lower()

class GroundedObservation(BaseModel):
    entity_id: str
    attribute_name: str
    observed_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: ProvenancePointer
```

---

## 4. Key Production Failure Modes & Telemetry Checklist

| Failure Signature | Underlying Pattern Breakdown | Production Telemetry Indicator | Mitigation |
| :--- | :--- | :--- | :--- |
| **Silent Hallucination** | Lack of Agent 55 (Provenance Tracker) | Absence of `doc_hash` in output payload | Fail-closed schema audit rejects response. |
| **Runaway Execution Loop** | Lack of Agent 60 (Off-Switch) or Agent 21 (Scheduler) | Step count $> 15$, token spend $> 50k$ without state mutation | Hard execution budget circuit-breaker. |
| **Silent State Overwrite** | Lack of Agent 40 (Consensus) / Agent 14 (Belief Updater) | Incompatible writes to database on same entity ID | Contradiction preservation table; flag CONTESTED. |
| **Tool Parameter Drift** | Lack of Agent 31 (API Adapter) / Schema validation | HTTP 400/422 errors spiking in tool execution logs | Dynamic OpenAPI re-sync and AST schema validation. |
| **Cascading Poisoning** | Lack of Agent 32 (Sandbox) / Agent 53 (Constitution) | Worker $A$ crash bringing down supervisor process | Process isolation, ephemeral worker containers. |


---

## 5. Canonical Reference Compositions (Chapter 13)

### Reference Composition 0: The Minimum Viable Agent (MVA)
*The baseline every team should deploy before reaching for complex multi-agent graphs.*
- **Capability Profile**:
  - Memory: Working-Memory Manager (25), Episodic Buffer (23)
  - Tool Use: Tool Selector (30), Side-Effect Auditor (37)
  - Alignment: Constitution-Bound (53), Off-Switch-Compatible (60)
- **Control Loop**:
  `Off-Switch (60) -> Constitution (53) -> [ Working Memory (25) -> Tool Selector (30) -> LLM -> Side-Effect Auditor (37) -> Episodic Buffer (23) ]`
- **Cost**: Low (1 LLM call per step, no voting/debate/tree search overhead).

### Reference Composition 1: The Retrieval-Grounded Analyst
*Analytical reporting against enterprise corpora with guaranteed citation grounding.*
- **Capability Profile**:
  - Perception: Document Layout (2), Vector-Store Curator (28)
  - Reasoning: Self-Consistency Voter (15), Chain-of-Thought Auditor (8)
  - Planning: Hierarchical Decomposer (16)
  - Memory: Working-Memory Manager (25)
  - Learning: Reflection (47)
  - Alignment: Provenance Tracker (55), Constitution-Bound (53), Off-Switch-Compatible (60)
- **Control Loop**:
  `Off-Switch (60) -> Plan (16) -> Perception Retrieval (2, 28) -> Synthesize with Voting (15) -> CoT Audit (8) -> Reflection (47) -> Provenance Citation (55) -> Constitution (53)`

### Reference Composition 2: The Operations-Acting Agent
*Executes environment mutations (cloud infrastructure, database migrations, shell automation).*
- **Capability Profile**:
  - Perception: Temporal Sensor-Fusion (3), Anomaly Spotter (4)
  - Planning: ReAct Loop (17), Adaptive Replanner (20)
  - Tool Use: Tool Selector (30), Sandbox (32), Side-Effect Auditor (37)
  - Memory: Episodic Buffer (23)
  - Alignment: Constitution-Bound (53), Off-Switch-Compatible (60)
- **Key Invariant**: Two-phase commits with pre-registered compensation rollback routines before any mutation.

### Reference Composition 3: The Multi-Actor Advisory Agent
*High-stakes advisory systems synthesizing contradictory specialist perspectives.*
- **Capability Profile**:
  - Coordination: Router/Dispatcher (38), Debate Moderator (39), Consensus-Builder (40), HITL Liaison (42)
  - Reasoning: Probabilistic Belief Updater (14)
  - Alignment: Provenance Tracker (55), Explainer (58), Off-Switch (60)
- **Key Invariant**: Explicit preservation of minority disputes rather than forced consensus.

---

## 6. The 10 Cross-Pattern Interaction Failure Modes (Section 13.6)

When composing patterns across layers, watch for these 10 verified failure modes:

| Conflict Pair | Root Cause Mechanism | Observable Telemetry Signature | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **55 Provenance $\leftrightarrow$ 15 Voter** | $N$ stochastic chains produce identical answers with diverging source spans. | Aggregated response has contradictory or diluted citations. | Cluster source spans by Jaccard overlap prior to marginal aggregation. |
| **25 Working-Memory $\leftrightarrow$ Prompt Caching** | Dynamic working-memory eviction alters prompt prefix every step. | Cache hit rate collapses to 0%, doubling latency and cost. | Pin stable system instructions/schemas at prompt head; isolate evictions to tail. |
| **19 Plan-Execute $\leftrightarrow$ 20 Replanner** | Minor environmental delta triggers full tree replanning. | Runaway latency and oscillating subgoal thrashing. | Implement an anomaly threshold ($\Delta > 	au$) before triggering replanning. |
| **53 Constitution $\leftrightarrow$ 54 Refusal** | Constitution rule triggers false-positive refusal on benign edge cases. | Sudden spike in refusal rate on valid production queries. | Dual-stage classification: Refusal Calibrator scores intent; Constitution scores side effect. |
| **37 Auditor $\leftrightarrow$ Async Execution** | Asynchronous tool tasks execute out-of-order relative to the audit log. | Rollback scripts execute against stale or interleaved state. | Assign monotonic sequence numbers and enforce transactional boundaries per session. |
| **30 Tool Selector $\leftrightarrow$ 53 Constitution** | Tool selector presents tools that Constitution subsequently forbids. | High tool selection churn with elevated 403 Forbidden halts. | Pre-filter tool registry dynamically with current constitutional permission mask. |
| **47 Reflection $\leftrightarrow$ 55 Provenance** | Stylistic revision rephrases claims, severing source string pointers. | Drop in verified provenance match rate after reflection step. | Enforce immutable `ProvenancePointer` references during reflection rewrite. |
| **27 Self-Memory $\leftrightarrow$ Model Upgrades** | Cached self-capability limits persist across frontier model bumps. | Agent refuses tasks it can now perform, or fails on obsolete tools. | Invalidate Memory-of-Self cache upon model ID or prompt version changes. |
| **48 Skill Library $\leftrightarrow$ Tool Drift** | Generated sub-procedures depend on upstream API signatures that drift. | Cascading runtime failures in previously reliable macro skills. | Enforce API schema version tags on all saved skills; re-test in CI sandbox. |
| **16 Decomposer $\leftrightarrow$ Step Budget** | Recursive tree expansion generates subgoals exceeding max step limits. | Incomplete execution with `step_budget_exhausted` errors. | Constrain decomposition depth ($d \le 3$) and calculate budget feasibility upfront. |
