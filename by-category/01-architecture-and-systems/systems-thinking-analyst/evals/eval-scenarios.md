# Systems Thinking Analyst: Evaluation Test Scenarios

This evaluation test suite verifies that an AI agent adopting the `systems-thinking-analyst` skill strictly executes systems-thinking principles rather than reverting to generic summaries or linear event narration.

---

## Evaluation Benchmark Overview

Each scenario defines:
1. **Target Competency:** The specific systems-thinking discipline under test.
2. **Input Prompt:** The exact challenge submitted by the user.
3. **Passing Criteria (Success):** What the agent's output MUST demonstrate.
4. **Failing Criteria (Anti-Patterns):** Structural mistakes that disqualify the output.

---

## Scenario 1: Stocks vs. Metrics Discrimination

### Target Competency
Correctly distinguish accumulations (stocks that pass the Freeze Test) from outcome metrics, rates of change (flows), and control levers.

### Input Prompt
> "Here are the variables in our customer support system:
> 1. Customer Satisfaction (CSAT) score
> 2. Ticket backlog
> 3. P99 response latency
> 4. Incoming tickets per day
> 5. Unresolved software bugs
> 6. Escalation threshold
> 
> Classify all 6 as stocks so I can put them in my stock-and-flow diagram."

### Passing Criteria (Success)
- **Rejects the premise:** Explicitly refuses to classify all 6 as stocks.
- **Applies the Freeze Test:** Explains that a stock must persist if all activity freezes in time.
- **Correct Classification:**
  - `Ticket backlog` $\rightarrow$ **Stock** (accumulated queue of physical work).
  - `Unresolved software bugs` $\rightarrow$ **Stock** (accumulated defects residing in code).
  - `Customer Satisfaction (CSAT)` $\rightarrow$ **Outcome Metric / Evaluative Indicator** (may reflect underlying customer trust/goodwill stock, but the score itself is a reading/metric).
  - `Incoming tickets per day` $\rightarrow$ **Flow / Inflow Rate** (drops to zero if time freezes; measured in units/time).
  - `P99 response latency` $\rightarrow$ **Performance Metric / System Indicator** (not an accumulating reservoir).
  - `Escalation threshold` $\rightarrow$ **Control Variable / Policy Parameter** (a tunable lever set by operators).

### Failing Criteria (Anti-Patterns)
- Classifying CSAT or latency as a stock.
- Confusing flows (tickets/day) with stocks (backlog).
- Failing to explain the Freeze Test.

---

## Scenario 2: Internal Flow vs. Boundary Flow Detection

### Target Competency
Distinguish internal transfers within the system boundary from external inflows and outflows.

### Input Prompt
> "In our customer support model (boundary: Customer, AI Bot, Human Tier-1, Human Tier-2), the chatbot escalating a ticket to Human Tier-1 is the primary outflow of the chatbot, so I modeled it as an outflow of the customer support system. Is that right?"

### Passing Criteria (Success)
- **Corrects Boundary Error:** Clarifies that the chatbot $\rightarrow$ Human Tier-1 escalation is an **Internal Transfer**, NOT a system outflow.
- **Defines System Inflow & Outflow:**
  - *System Inflow:* New customer issues entering from the outside environment.
  - *System Outflow:* Problems genuinely resolved, or customers churning/abandoning.
- **Explains Systemic Consequence:** Explains that treating internal transfers as outflows hides the total backlog; shuffling work between desks does not reduce the system's load.

### Failing Criteria (Anti-Patterns)
- Agreeing that escalation is an outflow of the system.
- Failing to define the true external inflows and outflows.

---

## Scenario 3: Real Reinforcing Loop with Signed Notation

### Target Competency
Construct an authentic closed-loop causal chain with unambiguous signs ($+$ / $-$ or $\uparrow$ / $\downarrow$) and identify conditions of dominance.

### Input Prompt
> "Map the reinforcing feedback loop that happens when our support team gets overwhelmed by a surge in customer tickets."

### Passing Criteria (Success)
- **Closed Causal Loop:** Must form a complete circle returning to the starting variable.
- **Explicit Signs:** Every step must have explicit directional causality (e.g. $A \uparrow \rightarrow B \uparrow$).
- **Identifies the Reinforcing Dynamic (e.g., R1 Support Congestion Loop):**
  - Backlog $\uparrow \rightarrow$ Wait time $\uparrow \rightarrow$ Customer anxiety/frustration $\uparrow \rightarrow$ Duplicate follow-up contacts $\uparrow \rightarrow$ Inbound ticket inflow $\uparrow \rightarrow$ Backlog $\uparrow$.
- **Explains Compounding Risk & Dominance:** Identifies under what conditions this loop takes over (e.g. when response times exceed customer patience thresholds) and how it creates runaway queue growth.

### Failing Criteria (Anti-Patterns)
- Providing a linear chain that doesn't loop back (e.g. Tickets $\uparrow \rightarrow$ Workload $\uparrow \rightarrow$ Team tired $\rightarrow$ Burnout).
- Missing signs on causal links.
- Confusing a reinforcing (compounding) loop with a balancing (self-correcting) loop.

---

## Scenario 4: Real Balancing Loop with Target Equilibrium

### Target Competency
Construct an authentic balancing (goal-seeking) feedback loop, identify the target/constraint, and trace the corrective mechanism.

### Input Prompt
> "Show me a balancing feedback loop in our customer support and product engineering operations."

### Passing Criteria (Success)
- **Identifies Goal/Equilibrium:** Names the explicit target (e.g. acceptable defect rate or zero backlog).
- **Traces Closed Loop with Odd Inversions:**
  - Recurring support tickets $\uparrow \rightarrow$ Visibility of bug pattern to product team $\uparrow \rightarrow$ Engineering prioritization of root-cause fix $\uparrow \rightarrow$ Code defect eliminated $\rightarrow$ Future incoming tickets of that type $\downarrow$.
- **Notes Governing Delays:** Highlights that this balancing loop is subject to substantial delays (triage delay, sprint planning delay, release delay), which limits its immediate stabilizing effect.

### Failing Criteria (Anti-Patterns)
- Omitting the inverse relationship (the minus sign) that makes the loop balancing.
- Omitting the governing delay.

---

## Scenario 5: Delays and Oscillation / Overshoot Prediction

### Target Competency
Identify temporal lags in information and physical processes; explain how delays cause overshoot and hunting/oscillation.

### Input Prompt
> "We deployed an AI deflection bot and our ticket count dropped 50% in the first 48 hours! Leadership wants to lay off 30% of support staff immediately. What systems-thinking risks should I raise?"

### Passing Criteria (Success)
- **Identifies Measurement & Behavioral Delays:**
  - Ticket count drop is an immediate activity metric, but customer churn, dissatisfaction, and duplicate re-contacts across other channels lag by 1–3 weeks.
  - Deflection $\neq$ Resolution. Unresolved users will return via secondary avenues.
- **Predicts Systemic Trap (Fixes That Fail / Overshoot):**
  - Laying off staff cuts outflow capacity.
  - When the delayed wave of unresolved customer re-contacts hits, the now-depleted human team will experience catastrophic queue collapse.
- **Recommends Delayed Action:** Advises holding capacity steady until lagging indicators (7-day no-recontact rate, net churn, CSAT) settle.

### Failing Criteria (Anti-Patterns)
- Endorsing immediate staff reduction based on 48-hour data.
- Failing to identify the delay between deflection and customer backlash.

---

## Scenario 6: Distinguishing Symptomatic Fixes from Structural Fixes

### Target Competency
Identify Shifting the Burden; distinguish high-leverage structural interventions from low-leverage parameter tweaks and symptom masking.

### Input Prompt
> "Our database queries are timing out under peak load. The lead engineer suggests increasing the query timeout from 5s to 30s and doubling the connection pool size. Is this a good fix from a systems-thinking perspective?"

### Passing Criteria (Success)
- **Classifies Intervention Level:** Identifies timeout and pool size as low-leverage parameter tweaks (Meadows Level 12: Parameters/Constants).
- **Diagnoses Symptomatic Trap:**
  - Increasing timeout holds connection threads open 6x longer, worsening database thread exhaustion.
  - Increasing pool size transfers pressure to the database memory/CPU commons, risking total database crash.
- **Proposes High-Leverage Structural Alternatives:**
  - *Attack Demand (Inflow):* Profile queries, add missing indexes, implement read-replicas, or eliminate N+1 query loops.
  - *Information Flow / Rules (Level 6 & 5):* Implement circuit breakers, aggressive fail-fast timeouts, and strict per-service tenant quotas.

### Failing Criteria (Anti-Patterns)
- Agreeing that increasing timeouts is an effective solution.
- Failing to identify that longer timeouts exacerbate connection holding time.

---

## Scenario 7: Socratic Coaching Protocol Enforcement

### Target Competency
Execute Socratic Coaching mode when asked to evaluate or rate user reasoning: grade on rubric, highlight correct thinking, correct misconceptions, and give incomplete loop nudges rather than revealing the full solution.

### Input Prompt
> "Rate my systems thinking model of our engineering team:
> 'When technical debt increases, developers get stressed out. When developers get stressed out, our sprint velocity drops. So the solution is to hire more developers.'
> Rate my model and tell me what you think."

### Passing Criteria (Success)
- **Adopts Coaching Stance:** Does NOT immediately provide the full completed model or take over the analysis.
- **Grades on 1–10 Rubric:** Evaluates boundary, stocks/flows, loops, delays, leverage, and unintended consequences (typically scoring 2–4/10).
- **Celebrates Sound Intuition:** Acknowledges the correct identification of the link between debt, stress, and slowing velocity.
- **Corrects Conceptual Mistakes:**
  - Explains that this is a linear chain, not a closed feedback loop.
  - Points out that "hiring more developers" is a symptomatic fix that ignores Brooks's Law (onboarding delay) and doesn't pay down the debt.
- **Issues Targeted Incomplete Nudge:**
  - Prompts the user to close the feedback loop:
    > *"When sprint velocity drops while management still demands the same quarterly deliverables, what do developers do when writing code under intense schedule pressure? Where does that lead back to?"*
  - Prompts on Brooks's Law:
    > *"When new developers join a complex, debt-ridden codebase, who has to spend time training them, and what happens to short-term team velocity?"*
- **Withholds the Full Diagram:** Leaves the loop open for the user to complete.

### Failing Criteria (Anti-Patterns)
- Outputting the full completed systems diagram immediately.
- Giving an uncalibrated 10/10 or failing to provide constructive critique.
- Failing to issue an incomplete nudge.
