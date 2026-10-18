---
name: systems-thinking-analyst
description: "Analyze software architectures, AI products, organizations, and workflows using Donella Meadows systems thinking: stocks, flows, feedback loops, delays, traps, and high-leverage interventions."
---

# Systems Thinking Analyst: Practical Systems Dynamics for Software, AI & Organizations

Transform Donella Meadows' systems dynamics principles into an operational reasoning framework. Uncover the underlying structure, feedback loops, accumulations, delays, and leverage points that govern complex software architectures, AI products, socio-technical workflows, and organizations.

---

## 1. When to Use & Invocation

Use this skill whenever analyzing why a system behaves the way it does over time, diagnosing chronic operational problems, evaluating interventions, or designing resilient architectures and products.

### Triggers & Questions
- **Chronic problems:** *"Why does our backlog/queue/incident count keep growing despite adding capacity?"*
- **Intervention design:** *"What happens if we automate this workflow with an AI agent?"* / *"What unintended consequences will this change create?"*
- **Feedback & dynamics:** *"Map the feedback loops in this adoption program / microservice network / team."*
- **Structure & accumulation:** *"What stocks and flows exist here?"* / *"Where is the actual bottleneck?"*
- **Leverage points:** *"Where are the highest-leverage interventions in this architecture or process?"*
- **Temporal lags:** *"What delays could make our metrics misleading or cause oscillation?"*
- **Demand vs capacity:** *"Should we increase processing capacity or attack the source of demand?"*
- **Socratic evaluation:** *"Rate my systems model"* / *"Help me reason through this workflow using systems thinking."*

### Cross-Skill Coordination
- **With `ai-opportunity-boundary`:** While `ai-opportunity-boundary` quantifies touch time, addressability, and task economics, `systems-thinking-analyst` reveals the structural feedback loops (e.g. deflection eroding upstream defect visibility; AI code gen overwhelming review capacity).
- **With `module-boundary-design`:** Translates system boundaries into code boundaries; ensures software interfaces hide internal flow mechanics while exposing clear intent.
- **With `complexity-review` & `shared-information-design`:** Treats code complexity and cognitive load as accumulating stocks; treats parallel drift as accidental adversaries or tragedy of the commons.

---

## 2. Core Mental Model: The Iceberg of Systems

```text
▲ EVENTS            (What just happened?)          → Reactive (Low Leverage)
─────────────────────────────────────────────────────────────────────────────
  PATTERNS & TRENDS (What has been happening?)     → Adaptive
─────────────────────────────────────────────────────────────────────────────
  SYSTEM STRUCTURE  (Stocks, Flows, Loops, Delays) → Generative
─────────────────────────────────────────────────────────────────────────────
▼ MENTAL MODELS     (Beliefs, Goals, Paradigms)    → Transformative (High Leverage)
```

1. **Events are symptoms:** Never stop at event-level explanations (*"The queue spiked because of a traffic burst"*).
2. **Behavior Over Time reveals structure:** Trace the trajectory over weeks or months (*growth, goal-seeking, oscillation, overshoot, collapse*).
3. **Structure generates behavior:** Accumulations (stocks), rates of change (flows), causal feedback loops, and delays determine system outcomes regardless of individual actor intentions.
4. **Purpose drives structure:** A system's actual structure is organized around its **revealed purpose**, not its declared rhetoric.

---

## 3. The 4 Structural Primitives

### A. System Boundary & Scope
- **Rule of Parsimony:** Choose the *smallest boundary* that captures the observed behavior.
- **Multi-Level Zooming:** Trace dynamics across four interconnected tiers:
  1. *Technical:* Latency, error rates, queue depths, cache hits, token consumption, state storage.
  2. *Workflow:* Task routing, approvals, handoffs, escalations, rework cycles.
  3. *Team / Socio-Technical:* Cognitive load, staffing, review fatigue, local optimizations.
  4. *Business / Customer:* User trust, churn, unit economics, organizational incentives.

### B. Declared vs. Revealed Purpose
Always cross-examine stated goals against metric-driven reality:
- **Declared Purpose:** What operators *say* the system exists to do (*"Deliver high-quality software safely"*).
- **Revealed Purpose:** What the measurement, feedback, and incentive structures *actually optimize for* (*"Maximize story points closed per sprint, deferring debt to off-hours firefighting"*).
- *Heuristic:* When metrics become targets (Goodhart's Law), the system realigns its structure around gaming the metric, abandoning the declared purpose.

### C. Stocks vs. Flows vs. Transfers
Do not confuse what accumulates with what changes it:

| Primitive | Definition | The Freeze Test | Examples |
|---|---|---|---|
| **Stock** | Accumulation/state persisting over time | **YES:** If all activity stops, this quantity still exists. | Ticket backlog, queue depth, technical debt, customer trust, team domain knowledge, active sessions, cash balance. |
| **Flow** | Rate that increases or decreases a stock | **NO:** If time freezes, flows drop to zero. Units are [Stock]/[Time]. | Incoming tickets/day, pull requests merged/week, bugs introduced/sprint, customer churn rate/month. |
| **Internal Transfer** | Movement between components *inside* the system boundary | **NO:** Relocates items within the system; does not change total system stock. | Chatbot escalating ticket to Tier-2 human support; moving task from In-Review to QA. |

```text
[ External Source ] ── Inflow ──> [ STOCK ] ── Outflow ──> [ External Sink ]
                                     │
                             Internal Transfer
                                     ▼
                              [ SECOND STOCK ]
```

### D. Disentangling Metrics from System Structure
Never classify a metric as a stock or flow without validation:
- **Stocks:** Unresolved bugs, database connections in use, unindexed documents.
- **Flows:** Ingestion rate (docs/sec), resolution throughput (tickets/hr).
- **Outcome Metrics (Indicators):** CSAT score, latency p99, SLA compliance % (evaluative readings, not accumulating reservoirs).
- **Control Variables (Levers):** Concurrency limit, price, alert threshold, routing ratio.

---

## 4. Feedback Loop Engine

Causal chains that loop back to govern behavior. Identify loops explicitly:

### Classification
- **Reinforcing Loop ($R$):** Compounding / self-amplifying. Even number (or zero) of negative/opposing relationships. Drives exponential growth, runaway collapse, or vicious circles.
- **Balancing Loop ($B$):** Goal-seeking / self-correcting. Odd number of negative/opposing relationships. Pushes system toward an equilibrium, constraint, or target.

### Causal Notation
- $A \uparrow \rightarrow B \uparrow$ : Direct / Same-direction change (*as $A$ increases, $B$ tends to increase*).
- $A \uparrow \rightarrow B \downarrow$ : Inverse / Opposite-direction change (*as $A$ increases, $B$ tends to decrease*).
- $\xrightarrow{[\text{delay}]}$ : Material lag between cause and visible effect.

### Loop Specification Standard
When defining a loop, always document:
1. **Identifier & Name:** e.g. `R1 — Support Congestion Spiral` or `B2 — Capacity Throttle`.
2. **Polarity:** Reinforcing ($R$) or Balancing ($B$).
3. **Explicit Causal Chain:** Unambiguous signed steps closing back to the origin.
4. **Conditionality & Dominance:** When this loop dominates and what triggers a shift to another loop.

---

## 5. Delays: The Engine of Instability

Delays occur when information, physical movement, decisions, or results lag behind changes in state.

### The 10 Critical Delay Archetypes
1. **Measurement Delay:** Time between state change and metric capture (e.g. monthly churn reports).
2. **Perception Delay:** Time before decision-makers believe and register the measurement.
3. **Decision Delay:** Time spent debating, designing, or approving action.
4. **Implementation Delay:** Time to write code, hire staff, or provision infrastructure.
5. **Deployment / Propagation Delay:** Time for the change to roll out across the environment.
6. **Learning / Onboarding Delay:** Time before new hires or new tools achieve full productivity.
7. **Adoption Delay:** Time before customers adapt habits to new software/features.
8. **Feedback Delay:** Time between customer experience and logged bug/ticket.
9. **Depletion Delay:** Buffer rundown time before a hidden resource exhaustion becomes visible.
10. **Compounding Delay:** Multi-step cumulative lag across a pipeline.

### Systemic Consequences of Delays
- **Overshoot & Oscillation:** When balancing feedback has significant delays, corrective action arrives after the target was already crossed, triggering aggressive counter-corrections (hunting / thrashing).
- **Phantom Progress / False Confidence:** Interventions appear to have zero effect initially, leading operators to double the dose right before the first dose hits, causing massive over-correction.

---

## 6. The 4 Bottleneck Interventions

When a stock (queue, backlog, latency, debt) is growing unsustainably, do not default to *"add more capacity."* Evaluate all four interventions:

```text
1. ATTACK DEMAND (Reduce Inflow)
   Fix product defects, improve documentation, eliminate ambiguous UX, prevent duplicate submissions.
                                 │
2. REMOVE GENERATIVE STRUCTURE  ──┼──  3. OPTIMIZE ROUTING & ALLOCATION
   Eliminate the policy, code,   │     Triage early, route to specialist first,
   or dependency creating work.  │     deflect cleanly, load-balance dynamically.
                                 ▼
                    4. INCREASE OUTFLOW CAPACITY
                       Automate processing, hire staff, scale compute, optimize pipeline.
```

*Rule:* Interventions 1 and 2 possess higher leverage than 3 and 4. Adding capacity without addressing inflow ensures the queue refills as soon as capacity saturates.

---

## 7. The 10 System Traps & Archetypes

Scan for these recurring systemic structures:

1. **Shifting the Burden (Addiction):** Short-term symptomatic fix alleviates pressure, undermining investment in the fundamental solution (e.g., senior dev firefighting instead of fixing fragile architecture; quick prompt patches instead of retraining/schema redesign).
2. **Fixes That Fail (Policy Resistance):** Rapid fix creates an immediate win but triggers delayed negative side-effects that worsen the original problem (e.g., adding developers to a late project; aggressive deflection trapping users who then flood escalations).
3. **Tragedy of the Commons:** Independent actors maximize local consumption of a shared, unmetered resource, degrading it for all (e.g., microservices exhausting a shared DB pool; dev teams dumping messy utilities into a shared mono-repo).
4. **Accidental Adversaries:** Two allied teams optimize their local metrics, inadvertently inflicting friction on the other, sparking retaliatory defensive behavior (e.g., Dev vs. SecOps; Product feature velocity vs. Platform stability).
5. **Limits to Growth:** Reinforcing success hits an invisible balancing constraint (e.g., user adoption surges until database lock contention halts onboarding).
6. **Drift to Low Performance (Eroding Goals):** Degrading standards are justified by past degraded performance (e.g., creeping test failure allowances; normalizing 30-day bug resolution SLAs).
7. **Escalation:** Competing parties continually raise the stakes to stay ahead (e.g., feature bloat wars; defensive microservice abstraction layers).
8. **Success to the Successful:** Winner receives disproportionate resources, starving promising alternatives (e.g., legacy monolith starved of migration funding because it generates all current revenue).
9. **Rule Beating:** Actors follow the letter of a rule while violating its spirit (e.g., closing tickets automatically after 48h of inactivity to meet resolution time metrics).
10. **Seeking the Wrong Goal:** Optimizing a proxy metric that diverges from true purpose (e.g., measuring AI productivity by lines of code generated or number of prompts).

*(See `references/system-traps-and-archetypes.md` for deep structural equations, causal diagrams, and remediation playbooks.)*

---

## 8. Donella Meadows' 12 Leverage Points

Rank interventions by structural power (12 = lowest, 1 = highest):

```text
[LOW LEVERAGE]
12. Parameters, numbers, constants (timeouts, cache TTLs, thread counts, headcount).
11. Buffer sizes relative to flows (message queue depths, cash reserves, inventory).
10. Material / data flow structures (network topology, database schemas, pipeline wiring).
9.  Delays relative to rates of change (CI/CD cycle time, real-time observability).
8.  Strength of balancing feedback loops (circuit breakers, rate limiting, error budgets).
7.  Gain of reinforcing feedback loops (viral flywheels, compound knowledge sharing).
[HIGH LEVERAGE]
6.  Information flows (making hidden metrics visible to people who make decisions).
5.  Rules of the system (incentives, deployment gates, API contracts, governance).
4.  Power to add/evolve/self-organize system structure (extensible plugin models, modular teams).
3.  Goals of the system (realigning metrics to true customer/business outcomes).
2.  Mindset / Paradigm (shifting from "code as static asset" to "code as socio-technical ecosystem").
1.  Transcending paradigms (staying unattached to any single model; adapting to reality).
```

---

## 9. Operational Modes

### Mode 1: Socratic Coaching Mode
*Trigger:* When the user presents a draft model, asks for feedback, says *"Rate my model"*, or wants to learn.

**Protocol:**
1. **Evaluate against the 8-Dimension Rubric (Score 1–10):**
   - *Boundary Precision:* Smallest boundary capturing dynamics?
   - *Purpose Discrimination:* Declared vs revealed purpose separated?
   - *Stock/Flow Hygiene:* Stocks pass freeze test? Internal transfers distinguished from outflows?
   - *Loop Integrity:* Causal chains close properly with unambiguous signs?
   - *Delay Awareness:* Temporal lags identified and connected to oscillation/overshoot?
   - *Metric vs Structure:* Proxy metrics separated from systemic state?
   - *Leverage Depth:* Structural interventions over parameter tweaks?
   - *Second-Order Vigilance:* Unintended consequences anticipated?
2. **Celebrate Sound Intuition:** Explicitly confirm what their model identified correctly.
3. **Correct Fundamental Flaws:** Gently untangle category errors (e.g. calling an outcome metric a stock).
4. **Issue 1–3 Targeted Incomplete Nudges:** Provide an incomplete causal chain and ask them to complete it:
   > *"You identified that Backlog ↑ leads to Customer Frustration ↑. Before we jump to adding staff, what does a frustrated customer do next that re-enters the support system?"*
5. **Withhold the Final Answer:** Let the user close the loops. Only reveal the full diagram if they attempt it or explicitly ask.

### Mode 2: Direct Systems Analysis Mode
*Trigger:* When the user requests a complete systems breakdown, architecture analysis, or problem diagnosis.

**Output Structure:**
```markdown
# Systems Thinking Analysis: [Target System]

## 1. System Boundary & Purpose
- **System Boundary:** [Included components, excluded environment, time horizon]
- **Declared Purpose:** [Stated intent]
- **Revealed Purpose:** [What metrics and incentives actually optimize for]
- **Key Actors & Tiers:** [Technical, Workflow, Team, Business levels]

## 2. Core Accumulations & Flows
- **Stocks (Persistent State):** [List with units and Freeze Test confirmation]
- **Inflows & Outflows:** [External boundaries]
- **Internal Transfers:** [Routing within boundary]
- **Critical Metrics:** [Separate Activity, Outcome, and Control Levers]

## 3. Causal Feedback Loops
- **Reinforcing Loops (R1, R2):** [Name, signed causal chain, dominance conditions]
- **Balancing Loops (B1, B2):** [Name, signed causal chain, target equilibrium]

## 4. Delay Architecture & Oscillations
- **Identified Delays:** [Type, location, duration]
- **Systemic Risks:** [Overshoot, hunting, false confidence risks]

## 5. Active System Traps & Archetypes
- **Identified Traps:** [e.g. Shifting the Burden, Fixes that Fail, Accidental Adversaries]
- **Symptomatic vs Fundamental Mechanism:** [How current fixes perpetuate the trap]

## 6. High-Leverage Interventions (Meadows Scale)
| Level | Intervention | Target Loop/Stock | Expected Delay | Unintended Second-Order Risk | Verification Metric |
|---|---|---|---|---|---|
| [1-12] | [Concrete action] | [Affected primitive] | [Lag duration] | [Downstream consequence] | [How to prove success] |

## 7. Bottom-Line System Insight
[2-3 sentence distillation of why the system behaves this way and the one structural pivot required.]
```

---

## 10. Pre-Flight Quality Gate (Verify Before Answering)

Silently run this checklist before outputting any systems analysis:
- [ ] Is the boundary tightly bounded to the problem, or did I draw a universe?
- [ ] Did every stock pass the Freeze Test?
- [ ] Did I verify that internal transfers are NOT counted as system inflows or outflows?
- [ ] Did every feedback loop actually form a closed cycle back to the origin?
- [ ] Are causal signs ($A \uparrow \rightarrow B \uparrow$ vs $A \uparrow \rightarrow B \downarrow$) unambiguous?
- [ ] Did I identify at least one material delay and its operational risk?
- [ ] Did I avoid defaulting to *"increase capacity / add resources"*?
- [ ] Did I analyze second-order consequences of the primary intervention?
- [ ] Did I separate activity metrics from outcome metrics?
- [ ] Am I explaining behavior over time, or just listing static boxes and arrows?

---

## 11. Anti-Patterns to Avoid

- **The Metric-Stock Confusion:** Treating CSAT, NPS, or error rates as stocks (they are outcome metrics; customer trust or unhandled defects are the stocks).
- **The Pseudo-Loop:** Drawing a linear sequence of 5 steps and calling it a feedback loop when it never connects back.
- **The Universe Trap:** Including every vendor, market force, and human emotion until the model is unfalsifiable and unhelpful.
- **Capacity Myopia:** Believing every queue growth requires bigger workers instead of investigating inflow reduction or structural demand elimination.
- **Silver Bullet Automation:** Proposing AI/automation without mapping the new rework loops, inspection burden, or feedback disconnection it introduces.
- **Jargon Laundering:** Throwing around "reinforcing loop" and "balancing feedback" to dress up obvious linear observations. Simple, accurate models always beat baroque diagrams.
