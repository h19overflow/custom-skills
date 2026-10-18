---
name: leverage-point-identification
description: "Identify, justify, and prioritize leverage points in an already-mapped system. Use when system stocks, flows, feedback loops, goals, rules, information flows, delays, constraints, paradigms, or system traps are already understood and the objective is to determine where intervention could meaningfully shift system behavior. Requires causal evidence for every proposed leverage point and must distinguish theoretical leverage from leverage accessible to the user."
---

# Leverage Point Identification

## Purpose

Identify where intervention can meaningfully alter the behavior of an already-understood system.

This skill answers:

> Where can the system be shifted?

> Why would changing this point alter system behavior?

> What causal mechanism makes it leverage?

> How much leverage does the user actually have from their position?

> What should be tested next?

This skill does not perform initial system mapping.

This skill does not treat every improvement opportunity as a leverage point.

This skill does not assume that the highest theoretical leverage point is the best practical intervention.

---

# Core Principle

A leverage point is not:

> "Something important."

A leverage point is:

> A place where a relatively focused intervention can alter an important causal structure and thereby produce disproportionate changes in system behavior.

Every leverage claim must therefore connect:

**Intervention → structural change → feedback change → behavioral change**

If that chain cannot be shown, do not call it a leverage point.

---

# Required Inputs

Prefer an existing system model containing:

* system purpose
* important stocks
* flows
* feedback loops
* delays
* rules
* information flows
* constraints
* goals
* actors
* incentives
* paradigms
* recurring behavior

If system traps have already been identified, use them.

Do not recreate the entire system map unless a missing relationship prevents leverage analysis.

---

# Observer and Agency Model

Always identify the user's position relative to the system.

The user is not an abstract omnipotent designer.

Determine whether the user is:

* system owner
* team member
* technical lead
* manager
* architect
* customer
* founder
* external advisor
* observer
* policymaker
* platform operator
* contributor

Then distinguish three levels of influence.

## Direct Control

The user can change this themselves.

Examples:

* architecture decisions
* documentation
* evaluation criteria
* agent prompts
* tooling
* process rules within their team

## Indirect Influence

The user cannot directly change it but can influence people who can.

Examples:

* team culture
* management policy
* organizational incentives
* product priorities

## Outside Current Agency

The user currently cannot realistically modify it.

Examples:

* national regulation
* company-wide compensation structure
* market structure
* executive-level paradigm

Do not recommend an inaccessible leverage point as the primary action without explaining how influence could first be built.

---

# Step 1 — State the Behavior to Change

Before searching for leverage, define the undesirable or desired behavior.

Use:

> Current recurring behavior:

> Desired behavioral shift:

Examples:

Current:

> Technical debt grows faster than the team can remove it.

Desired:

> Technical debt remains bounded while delivery capacity remains sustainable.

Avoid vague goals such as:

> "Make the system better."

---

# Step 2 — Identify the Dominant Causal Structure

Determine what currently generates the behavior.

Prefer one or two dominant structures.

Examples:

Technical debt ↑
→ development speed ↓
→ deadline pressure ↑
→ shortcuts ↑
→ technical debt ↑

or:

Poor quality
→ lower expectations
→ weaker corrective effort
→ poorer quality

Do not propose leverage points before identifying what mechanism must change.

---

# Step 3 — Identify Candidate Intervention Points

Search across Meadows-style leverage categories from lower structural depth to higher structural depth.

Do not assume higher automatically means better.

---

# Leverage Categories

## 12 — Parameters

Examples:

* thresholds
* budgets
* prices
* limits
* retry counts
* temperature settings
* timeout values
* headcount
* token limits

Ask:

> Would changing this alter only the magnitude of behavior while preserving the same structure?

Usually lower leverage.

Do not dismiss parameters if the system is near a critical threshold.

---

## 11 — Buffers

Stocks that provide resilience between changing flows.

Examples:

* cash reserves
* queue capacity
* inventory safety stock
* spare compute
* review capacity
* error budgets

Ask:

> Would increasing or decreasing this buffer materially change how quickly the system reacts to disturbances?

Beware:

Larger buffers may improve resilience while hiding underlying problems.

---

## 10 — Physical or Structural Arrangement

How material or technical components are arranged.

Software examples:

* service boundaries
* queue architecture
* shared databases
* synchronous versus asynchronous communication
* centralized versus distributed execution

Ask:

> Does the current structure mechanically constrain the behavior?

Do not confuse architectural redesign with automatically high leverage.

Structural changes may be expensive and difficult to reverse.

---

## 9 — Delays

Time between action, feedback, and response.

Examples:

* delayed evaluation
* slow incident detection
* delayed customer feedback
* slow deployment
* long review cycles
* agent response latency

Ask:

> Does the system make decisions using information that is already outdated?

Strong evidence exists when shortening or correctly accounting for the delay would change oscillation, overshoot, instability, or corrective behavior.

---

## 8 — Balancing Feedback Strength

Mechanisms that resist deviation from a target.

Examples:

* quality checks
* autoscaling
* budget controls
* rate limits
* code review
* evaluation gates

Ask:

> What mechanism attempts to restore the system when it drifts?

Then:

> Is that mechanism too weak, too strong, delayed, or aimed at the wrong target?

---

## 7 — Reinforcing Feedback Strength

Self-amplifying loops.

Examples:

Technical debt spiral.

Customer referral growth.

Agent retry storms.

Knowledge accumulation.

Ask:

> Which loop compounds itself?

Possible interventions:

* weaken harmful reinforcement
* strengthen beneficial reinforcement
* introduce a balancing mechanism

Do not simply "break the loop" without checking what useful function it serves.

---

## 6 — Information Flows

Who knows what, when, and in what form.

Examples:

* exposing model costs to developers
* making technical debt visible
* surfacing customer complaints to product teams
* showing agents shared state
* exposing downstream failures to upstream services

Ask:

> Would behavior change if an actor received information they currently lack?

Information is leverage only when someone can act on it.

Do not treat dashboards without behavioral consequences as leverage.

---

## 5 — Rules

Constraints determining what actors are allowed, rewarded, required, or punished for doing.

Examples:

* deployment requirements
* code review rules
* budget approval rules
* agent tool permissions
* evaluation gates
* incentives
* escalation rules

Ask:

> Which behavior exists because the current rules make it rational?

Strong evidence exists when actors behave differently under different rules while their underlying capabilities remain unchanged.

---

## 4 — Self-Organization

The system's ability to modify its own structure.

Examples:

* teams creating new processes
* agents generating specialized subagents
* modular systems allowing new components
* employees creating automation
* markets creating new niches

Ask:

> Can the system learn, reorganize, or create new structures?

Intervention may increase:

* experimentation
* modularity
* learning
* autonomy
* recombination

Be cautious:

More self-organization can also increase instability.

---

## 3 — Goals

The objective toward which the system optimizes.

Examples:

From:

> maximize tickets closed

to:

> maximize customer problems actually resolved

or:

> maximize features shipped

to:

> maximize sustainable customer value delivered

Ask:

> If the system achieved its stated goal perfectly, would the resulting behavior actually be desirable?

A goal change is leverage when lower-level behavior follows from optimization toward the existing goal.

---

## 2 — Paradigms

Deep assumptions determining how actors interpret the system.

Examples:

Old paradigm:

> Humans perform the work and software assists them.

New paradigm:

> Humans define outcomes, judgment boundaries, and verification while intelligent systems perform portions of execution.

Ask:

> What assumption makes the current rules, goals, and structures appear natural?

A paradigm is not merely an opinion.

It must explain why multiple lower-level system choices exist.

---

## 1 — Transcending Paradigms

Ability to recognize that paradigms themselves are models rather than absolute truths.

Use sparingly.

Do not label intellectual flexibility as leverage without showing how it affects system decisions.

---

# Step 4 — Require Causal Proof

Every candidate leverage point must include:

## Current structure

What currently happens?

## Intervention

What exactly changes?

## First-order effect

What immediately changes?

## Feedback effect

Which loop is strengthened, weakened, redirected, or created?

## Behavioral consequence

What recurring system behavior should change?

Use:

> Intervention
> → Structural effect
> → Feedback-loop effect
> → Behavioral outcome

Example:

Expose technical-debt growth during sprint planning
→ debt becomes visible during prioritization
→ teams allocate capacity before deadline pressure becomes extreme
→ technical-debt reinforcing loop weakens
→ debt accumulation stabilizes

Without this chain, mark the leverage claim as unproven.

---

# Step 5 — Distinguish Leverage From Importance

Something may be extremely important while still offering weak leverage.

Example:

> Customer satisfaction is important.

But:

> "Improve customer satisfaction"

is not a leverage point.

Instead:

Customer complaints are currently delayed three months before reaching product teams.

Reducing that information delay may be leverage.

Always ask:

> What mechanism changes?

---

# Step 6 — Distinguish Leverage From Scale

Large intervention does not mean high leverage.

Example:

Hiring 100 engineers can create a large effect.

That does not automatically mean hiring is a high-leverage intervention.

Likewise:

Changing one information flow may cost almost nothing but restructure behavior across an organization.

Evaluate structural depth, not expenditure.

---

# Step 7 — Evaluate Practical Leverage

Do not rank interventions solely by Meadows' hierarchy.

For every candidate assess:

| Dimension        | Question                                   |
| ---------------- | ------------------------------------------ |
| Structural depth | How deeply does it alter system behavior?  |
| Evidence         | How strong is the causal proof?            |
| Reach            | How much of the system is affected?        |
| User agency      | Can the user actually influence it?        |
| Feasibility      | Can it realistically be implemented?       |
| Reversibility    | Can it be undone if wrong?                 |
| Delay            | How long before effects become observable? |
| Side effects     | What else could change?                    |
| Resistance       | Which actors or loops may oppose it?       |

Do not produce a numerical score unless explicitly requested.

---

# Step 8 — Identify the Leverage Path

A high-level leverage point may not be directly accessible.

Find the path toward it.

Example:

Desired paradigm:

> AI is part of normal engineering execution.

User cannot directly change company culture.

Possible path:

Pilot AI workflow
→ demonstrate measurable result
→ team adoption
→ management confidence
→ workflow rules change
→ organizational expectations change
→ paradigm gradually shifts

This is called a leverage path.

Always distinguish:

> Ultimate leverage point

from:

> Accessible first intervention

---

# Step 9 — Check for System Resistance

Before recommending movement, ask:

> What feedback loops will resist this intervention?

Possible resistance:

* incentives
* competing goals
* organizational politics
* resource constraints
* habit
* risk perception
* information asymmetry
* sunk costs
* existing success metrics
* other system traps

A leverage point that triggers strong resistance may require an indirect intervention first.

---

# Step 10 — Look for Trap-Leverage Connections

If a known system trap exists, use it to narrow candidate leverage points.

Examples:

## Drift to Low Performance

Possible leverage:

* preserve absolute standards
* expose historical performance
* prevent expectations from tracking declining performance

## Shifting the Burden

Possible leverage:

* weaken dependence on symptomatic solution
* strengthen fundamental solution
* expose long-term cost of symptom treatment

## Tragedy of the Commons

Possible leverage:

* visibility of total resource usage
* usage rules
* shared incentives
* ownership of resource health

## Rule Beating

Possible leverage:

* redesign the rule
* align measurement with system purpose
* measure outcomes rather than proxies

## Policy Resistance

Possible leverage:

* align goals
* expose competing incentives
* redesign shared objective

## Limits to Growth

Possible leverage:

* identify and relieve limiting constraint
* weaken harmful reinforcing growth
* redesign growth mechanism

Do not mechanically assign leverage based only on trap name.

Prove the causal connection.

---

# Step 11 — Consider the User's Mental Model

Because the user is also an observer of the system, inspect whether their own paradigm may constrain the analysis.

Ask:

> What assumptions is the user currently making about how this system works?

Examples:

* more agents = more capability
* more engineers = more throughput
* more automation = more productivity
* stricter rules = better quality
* more data = better AI
* higher utilization = greater efficiency

Do not challenge assumptions merely for novelty.

Challenge them only when the mapped system provides contradictory evidence.

Distinguish:

**System leverage**

from:

**Observer paradigm correction**

Sometimes the highest-value intervention is improving how the decision maker perceives the system before changing the system itself.

---

# Step 12 — Require an Observable Prediction

Every recommended intervention must produce a testable expectation.

Use:

> If this is genuinely a leverage point, then after intervention X we should observe behavior Y changing through mechanism Z.

Example:

> If delayed quality feedback is a major leverage point, reducing evaluation latency should decrease repeated implementation errors before total engineering capacity increases.

If no observable prediction can be generated, confidence should be reduced.

---

# Step 13 — Prefer Small Probes Before Large Changes

Where possible, test leverage using a reversible experiment.

Example:

Before:

> Change the entire company's engineering paradigm.

Try:

> Apply the new workflow to one team for four weeks and observe cycle time, rework, quality, and adoption behavior.

Use small experiments to improve the system model.

Do not confuse pilot size with leverage magnitude.

---

# Candidate Classification

Classify every candidate as one of:

### Confirmed leverage candidate

Strong causal structure and evidence.

### Plausible leverage candidate

Mechanism is reasonable but requires validation.

### Weak leverage

Can improve outcomes but does not materially alter system structure.

### Not a leverage point

Important variable with no demonstrated intervention mechanism.

### Inaccessible leverage

Potentially powerful but outside the user's current agency.

---

# Required Output

## 1. Behavioral Target

**Current behavior:**
What the system repeatedly does.

**Desired behavior:**
What should change.

---

## 2. Dominant System Structure

Show only the important causal mechanism.

Example:

Workload ↑
→ deadline pressure ↑
→ shortcuts ↑
→ technical debt ↑
→ performance ↓
→ workload ↑

---

## 3. User Position

**Role in system:**
Who the user is relative to the system.

**Direct control:**
What they can change directly.

**Influence:**
What they can influence indirectly.

**Outside current control:**
What currently requires others.

---

## 4. Candidate Leverage Points

For each candidate:

### Candidate: [Name]

**Leverage category:**
Information flow / rule / goal / paradigm / feedback loop / etc.

**Current structure:**
What currently produces the behavior.

**Proposed shift:**
What should change.

**Why this is leverage:**
Explain the causal mechanism.

**Causal proof:**

Intervention
→ structural change
→ feedback change
→ behavior change

**Evidence:**
What observations from the system support the claim.

**User agency:**
Direct / indirect / inaccessible.

**Confidence:**
High / moderate / hypothesis.

**Expected observable effect:**
What should happen if the diagnosis is correct.

---

# 5. Leverage Map

Summarize:

| Candidate | Category | Structural depth | Evidence | User agency | Main risk |
| --------- | -------- | ---------------- | -------- | ----------- | --------- |

Do not select solely based on depth.

---

# 6. Recommended Leverage Path

Describe:

**Ultimate structural shift**

↓

**Intermediate change**

↓

**First accessible intervention**

Prefer the smallest intervention that tests the underlying hypothesis.

---

# 7. Resistance Map

Identify:

* actors likely to resist
* loops likely to counteract the intervention
* delays before evidence appears
* unintended consequences
* existing traps that may absorb the intervention

---

# 8. Validation Plan

For the first intervention state:

**Change:**
What will be modified.

**Prediction:**
What should change.

**Measurement:**
How it will be observed.

**Time horizon:**
When the effect should reasonably appear.

**Falsification:**
What result would indicate that this is not actually the leverage point.

---

# 9. Final Assessment

Use:

**Behavior being changed:**
[Behavior]

**Dominant causal structure:**
[Structure]

**Strongest supported leverage point:**
[Leverage]

**Why:**
[Short causal explanation]

**User's first move:**
[Accessible intervention]

**What would prove this wrong:**
[Falsification condition]

---

# Strict Rules

## Rule 1

Never call something leverage because it appears high on Meadows' hierarchy.

Prove the mechanism.

## Rule 2

Never recommend changing a paradigm without identifying the existing paradigm.

## Rule 3

Never claim a goal change is leverage without showing which downstream behaviors are produced by the current goal.

## Rule 4

Never claim information is leverage unless an actor can use that information to change behavior.

## Rule 5

Never call a rule leverage unless it alters incentives, constraints, or permitted behavior.

## Rule 6

Never confuse a desired outcome with an intervention.

"Increase quality" is not a leverage point.

## Rule 7

Never assume deeper leverage means easier, safer, or more appropriate intervention.

## Rule 8

Never ignore the user's actual power within the system.

## Rule 9

Never recommend system-wide restructuring before testing whether a smaller intervention can validate the causal hypothesis.

## Rule 10

Never optimize a subsystem without checking effects on the larger system.

## Rule 11

Always identify likely system resistance.

## Rule 12

Every primary recommendation must produce a falsifiable prediction.

## Rule 13

If evidence is insufficient, say:

> "Potential leverage point — not yet demonstrated."

Do not manufacture certainty.

---

# AI and Agentic System Leverage Checks

When analyzing AI systems, inspect specifically:

### Goals

Are agents optimizing the same overall objective?

### Rules

Who may call which tools?

What conditions permit delegation, retries, escalation, or termination?

### Information

Do agents see the state required to coordinate?

### Feedback

Are evaluation signals fast enough to influence behavior?

### Reinforcement

Does success cause more traffic, context, tools, or autonomy to be allocated?

### Delays

How long between agent action and evaluation?

### Shared resources

Context, compute, rate limits, reviewer attention.

### Paradigm

Is the system designed around:

> humans performing tasks with AI assistance

or:

> humans governing systems performing tasks?

Do not assume the second paradigm is automatically appropriate.

Tie the paradigm to the desired system behavior.

---

# Software Architecture Leverage Checks

Inspect whether behavior could be shifted through:

* ownership boundaries
* service interfaces
* information visibility
* deployment feedback
* observability
* testing rules
* queue policies
* architecture decision rules
* technical-debt visibility
* incentives around delivery
* shared platform constraints
* modularity
* team boundaries

Prefer mechanisms over technologies.

Do not claim:

> "Use Kafka"

or:

> "Add an agent"

is leverage.

Explain which system relationship the technology changes.

---

# Quality Standard

A weak analysis says:

> "Changing team culture is a high-leverage paradigm shift."

A strong analysis says:

> "The team currently treats feature throughput as the primary indicator of engineering performance. This belief drives sprint targets, review behavior, tolerance for technical debt, and management reporting. Changing only review rules is likely to be overridden by the same throughput goal. A shift toward sustainable delivery as the operating goal could alter several downstream rules. However, the user cannot directly change the organizational goal, so the first accessible intervention is to expose the relationship between technical debt, rework, and delivery speed in sprint reporting and test whether decision behavior changes."

The skill should always prefer the second form.

---

# Governing Question

At every stage ask:

> What exactly changes in the system if we intervene here, and why should that produce a different behavior?

If that cannot be answered clearly, leverage has not yet been demonstrated.
