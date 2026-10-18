---
name: system-trap-identification
description: "Identify recurring system traps in an already-mapped system. Use when stocks, flows, feedback loops, actors, goals, incentives, constraints, and delays are already known and the task is to determine whether the observed structure matches known system traps. Do not remap the system and do not jump directly to solutions."
---

# System Trap Identification

## Purpose

Inspect an existing system model and determine whether its structure produces one or more recurring system traps.

This skill is diagnostic.

It answers:

> "What recurring structural trap, if any, is this system falling into?"

It does **not** perform general system mapping.

It does **not** assume a trap must exist.

---

# Expected Input

Prefer an existing system description containing some combination of:

* important stocks
* inflows and outflows
* feedback loops
* actors or subsystems
* goals
* incentives
* rules
* shared resources
* delays
* recurring behaviors
* observed outcomes

Incomplete maps are acceptable if there is enough evidence to evaluate a trap.

---

# Core Rule

Never identify a trap because an example merely resembles one superficially.

A trap requires a **matching causal structure**.

Use:

**Observed behavior → causal structure → trap signature**

Not:

**Observed behavior → familiar trap name**

---

# Identification Process

## 1. Identify the Recurring Behavior

Ask:

> What undesirable behavior keeps reproducing itself?

Examples:

* quality continuously declines
* agents repeatedly counteract each other
* technical debt keeps returning
* one subsystem keeps receiving more resources
* shared compute becomes increasingly overloaded
* temporary fixes become permanent
* teams optimize metrics while harming the real objective

Ignore isolated incidents unless they reveal a recurring mechanism.

---

## 2. Find the Loop Producing It

Locate the feedback structure responsible for the behavior.

Express it briefly:

> A ↑ → B ↓ → C ↑ → A ↑

or:

> A ↑ → B ↑ → C ↓ → A ↓

Do not require every intermediate variable.

Capture only enough structure to explain the behavior.

---

## 3. Compare Against Trap Signatures

Evaluate each plausible trap.

Do not scan mechanically through every trap if only a few are relevant.

---

# Trap Signatures

## Policy Resistance

### Signature

Multiple actors pursue different goals and react to each other's interventions.

Each actor's attempt to improve its own outcome causes others to push back.

### Look for

* competing subsystem goals
* repeated corrective actions
* interventions being neutralized
* oscillation or stalemate
* actors responding rationally from their own perspective

### AI / Software Example

A cost-routing agent increasingly selects cheaper models.

A quality-control agent rejects more outputs and reruns them using stronger models.

The cost optimizer responds by becoming even more aggressive.

Total cost does not improve.

### Confirm With

> If one actor stopped pushing toward its goal, would the resistance substantially decrease?

---

## Tragedy of the Commons

### Signature

Several actors independently benefit from consuming a shared limited resource while the cost of depletion is distributed across everyone.

### Look for

* shared resource
* individual incentives to consume more
* no actor responsible for total usage
* resource degradation
* rational local decisions causing bad global outcomes

### AI / Software Examples

* agents competing for context window
* teams consuming shared GPU capacity
* services exhausting shared API quotas
* agents filling shared memory with locally useful information

### Confirm With

> Does each actor benefit from additional usage while bearing only part of the resulting cost?

---

## Drift to Low Performance

### Signature

Actual performance falls.

Instead of restoring performance, expectations or standards gradually fall toward current performance.

Lower expectations reduce corrective pressure, enabling further decline.

### Look for

* tolerated exceptions
* gradually lowering quality bars
* "temporary" degradation becoming normal
* benchmarks being adjusted downward
* expectations adapting to poor performance

### Structure

Actual performance ↓
→ perceived acceptable performance ↓
→ corrective effort ↓
→ actual performance ↓

### Software Examples

* failing tests becoming accepted
* increasingly poor latency becoming normal
* code review standards weakening
* "we'll fix it later" becoming permanent culture

### Confirm With

> When performance falls, does the organization primarily lower expectations instead of restoring performance?

---

## Escalation

### Signature

Two actors compare themselves against each other.

An increase by one causes the other to increase, which causes the first to increase again.

### Look for

* relative rather than absolute targets
* competitive response
* arms-race behavior
* growing resource expenditure
* no natural stopping point

### AI / Software Examples

Agent A adds more validation because Agent B makes mistakes.

Agent B becomes more elaborate to satisfy Agent A.

Agent A adds even more validation.

System complexity escalates.

### Confirm With

> Would one side stop escalating if the other stopped?

---

## Success to the Successful

### Signature

A subsystem performing slightly better receives additional resources.

Those resources improve its performance further.

The competing subsystem receives fewer resources and weakens.

### Look for

* shared resource pool
* performance-based allocation
* initial small advantage
* reinforcing concentration
* weaker alternatives losing learning opportunities

### AI / Software Examples

One agent initially performs slightly better.

It receives:

* more context
* more tools
* more optimization effort
* more traffic

Other agents receive less data and fewer opportunities to improve.

### Confirm With

> Is past success influencing future resource allocation in a way that creates more success?

---

## Shifting the Burden

### Signature

A symptomatic solution quickly reduces visible pain.

Because symptoms improve, investment in the fundamental solution decreases.

The underlying problem remains or worsens.

### Look for

* repeated quick fixes
* dependence on patches
* fundamental capability weakening
* symptoms repeatedly returning
* short-term relief beating long-term repair

### AI / Software Examples

* increasing context size instead of improving retrieval
* adding prompt instructions instead of fixing data quality
* adding agents instead of clarifying responsibilities
* restarting services instead of resolving memory leaks
* increasing retries instead of fixing unreliable dependencies

### Structure

Problem
→ symptomatic fix
→ temporary relief
→ less pressure for fundamental fix
→ underlying problem persists
→ greater dependence on symptomatic fix

### Confirm With

> Does using the quick fix make the fundamental fix less likely?

---

## Rule Beating

### Signature

Actors satisfy the literal measurement or rule while violating its intended purpose.

### Look for

* metric gaming
* technically compliant but harmful behavior
* optimization around evaluation criteria
* incentives misaligned with actual goals

### AI / Software Examples

* coding agents hack tests instead of fixing functionality
* teams maximize ticket count by splitting trivial work
* agents optimize benchmark scores without improving real-world performance
* support teams close tickets quickly while unresolved problems remain

### Confirm With

Ask:

> Could an actor score well under the rule while performing badly against the actual goal?

If yes, investigate rule beating.

---

## Limits to Growth

### Signature

A reinforcing growth process initially succeeds.

Growth eventually activates a balancing constraint that slows, stops, or reverses it.

### Look for

* initial exponential or rapid improvement
* diminishing returns
* hidden capacity constraint
* growing coordination overhead
* resource saturation

### AI / Software Examples

More agents
→ greater parallelism
→ faster work

until:

More agents
→ coordination overhead
→ duplicated work
→ contention
→ slower system

### Confirm With

> What becomes scarce or overloaded specifically because growth succeeds?

---

# Trap Discrimination

Several traps can look similar.

Use these distinctions.

| Observation                                          | Likely trap               |
| ---------------------------------------------------- | ------------------------- |
| Different actors keep undoing each other's actions   | Policy Resistance         |
| Everyone overuses the same shared resource           | Tragedy of the Commons    |
| Expectations decline alongside performance           | Drift to Low Performance  |
| Two actors keep increasing in response to each other | Escalation                |
| Winners receive increasingly more resources          | Success to the Successful |
| Quick fix weakens investment in real fix             | Shifting the Burden       |
| Metric is satisfied while purpose is violated        | Rule Beating              |
| Growth hits a self-created constraint                | Limits to Growth          |

---

# Multi-Trap Systems

Do not assume traps occur independently.

A system may contain multiple connected traps.

Example:

More workload
→ more shortcuts
→ quick patches
→ **Shifting the Burden**

which causes:

Technical debt ↑
→ quality ↓
→ lower accepted standards
→ **Drift to Low Performance**

which may eventually cause:

Teams gaming delivery metrics
→ **Rule Beating**

When multiple traps exist:

1. identify them separately
2. show how they interact
3. identify which trap appears upstream

Prefer explaining the causal chain over producing a long trap list.

---

# Confidence Standard

For every identified trap assign:

### High confidence

The defining feedback structure is clearly visible.

### Moderate confidence

Most structural characteristics are present, but one important relationship is uncertain.

### Low confidence / hypothesis

The behavior resembles the trap but the feedback structure has not been established.

Never call a low-confidence hypothesis a confirmed trap.

---

# False Positive Checks

Before confirming a trap, ask:

### Policy Resistance

Could this simply be implementation failure rather than competing goals?

### Tragedy of the Commons

Is the resource actually shared and limited?

### Drift to Low Performance

Are expectations genuinely falling, or is performance simply falling?

### Escalation

Are the actors responding to each other, or independently increasing?

### Success to the Successful

Are resources actually being reallocated because of previous success?

### Shifting the Burden

Does the symptomatic solution actually weaken the fundamental solution?

### Rule Beating

Is someone optimizing the rule, or merely performing poorly?

### Limits to Growth

Is there a balancing constraint produced or exposed by growth?

---

# AI Agent Special Checks

When analyzing agentic systems, explicitly inspect for:

### Goal conflicts

Different agents optimizing incompatible objectives.

Possible trap:
**Policy Resistance**

### Shared resource competition

Agents consuming:

* tokens
* context
* API quotas
* compute
* memory
* human review attention

Possible trap:
**Tragedy of the Commons**

### Agent proliferation

Adding more agents initially improves parallelism but later creates communication and coordination overhead.

Possible trap:
**Limits to Growth**

### Evaluation gaming

Agents optimize the evaluator rather than the real task.

Possible trap:
**Rule Beating**

### Retry dependence

Retries hide underlying reliability problems.

Possible trap:
**Shifting the Burden**

### Dominant agent reinforcement

One successful agent gets more tools, traffic, context and optimization opportunities.

Possible trap:
**Success to the Successful**

### Quality normalization

Poor agent outputs gradually become accepted because expectations are reduced.

Possible trap:
**Drift to Low Performance**

### Agent-response escalation

Agents repeatedly increase verification, critique, retries or tool usage in response to one another.

Possible trap:
**Escalation**

---

# Required Output

## Observed Pattern

Describe the recurring behavior in 1–3 sentences.

## Relevant Feedback Structure

Show only the causal chain required to explain the behavior.

Example:

Technical debt ↑
→ development speed ↓
→ deadline pressure ↑
→ shortcuts ↑
→ technical debt ↑

## Trap Diagnosis

| Trap | Confidence | Key evidence |
| ---- | ---------- | ------------ |

Include only traps supported by evidence.

## Why It Matches

For each identified trap explain:

1. what the defining structure is
2. where that structure appears in this system
3. what recurring behavior it explains

## Competing Explanation

If another trap or ordinary failure mode could plausibly explain the behavior, mention it.

Example:

> This resembles Shifting the Burden more strongly than Limits to Growth because repeated symptomatic fixes reduce pressure to address the fundamental architecture problem.

## Missing Evidence

Identify anything that would materially change the diagnosis.

## Final Diagnosis

Use:

> **Primary trap:**
> **Supporting structure:**
> **Confidence:**
> **What would falsify this diagnosis:**

---

# Do Not

* remap the entire system unless required to understand missing evidence
* identify every possible trap
* force behavior into Meadows terminology
* mistake symptoms for traps
* treat one-time incidents as system traps
* assume bad outcomes imply bad actors
* jump directly to leverage points
* recommend solutions unless explicitly requested
* use trap names without showing their causal structure

---

# Quality Bar

A good diagnosis should allow someone to say:

> "I can see exactly why this is that trap."

A weak diagnosis sounds like:

> "This seems like Shifting the Burden because the team keeps using quick fixes."

A strong diagnosis sounds like:

> "The team repeatedly adds prompt-level patches when retrieval fails. These patches temporarily improve output, which reduces urgency to improve retrieval quality. Retrieval therefore remains unreliable, creating future failures and greater dependence on prompt patches. This matches the feedback structure of Shifting the Burden."
