---
name: ai-opportunity-boundary
description: "Use whenever someone wants to discover, evaluate, prioritize, or redesign AI automation opportunities in a process, workflow, task, or recurring decision—even if they say “build an AI agent,” provide a large research bundle, ask what is not automated by AI, want to enhance existing automation, or need an ROI/capacity case. Synthesize mixed evidence, quantify workload and human effort, distinguish capacity from savings, test addressability and uncertainty, use credible benchmarks when permitted, and produce a bounded, measurable opportunity and investment map."
---

# AI Opportunity Boundary

Find, quantify, bound, economically evaluate, and validate AI opportunities. Do not begin with a model, chatbot, or agent. Begin with evidence, outcomes, boundaries, workload, bottlenecks, and decisions.

The goal is not merely **“Can this be automated?”** It is **“Is this work important enough to change, how much exists, what is realistically addressable, what outcome could improve, what human work remains, and how do we know?”**

## Flexible input and evidence discipline

Accept any mix of problem statements, interviews, transcripts, process maps, SOPs, tickets, logs, metrics, spreadsheets, policies, automation inventories, time studies, event histories, document revisions, approval timestamps, audit logs, or external research.

Inventory sources before concluding. Preserve attribution, dates, definitions, contradictions, and uncertainty. Classify material claims as **Observed** (measured/witnessed), **Reported** (claimed by a participant), **Inferred** (reasoned interpretation), or **Unknown** (not established). Classify quantitative inputs as **measured**, **reported**, **benchmarked**, **estimated**, or **scenario assumption**. Never silently turn an estimate or external benchmark into an internal observation.

For sparse input, produce a provisional analysis, show unknowns, and ask only questions that could change the recommendation. For large input, cluster and deduplicate it, retain the evidence trail, and surface conflicts. Use proportional depth: compact analysis for small, low-risk work; full quantitative, benchmark, addressability, economics, and sensitivity analysis for strategic, high-volume, high-cost, regulated, or portfolio decisions.

## Core method

### 1. Start with outcomes

State separately:

- **Business outcome:** measurable organizational result;
- **Customer/recipient outcome:** what the person receiving the work needs;
- **Job-to-be-done:** progress someone is trying to make.

Reject “use AI,” “deploy an agent,” or “make it smarter” until connected to an outcome and metric.

### 2. Build the work hierarchy

Map only as deeply as evidence requires:

`business outcome → customer outcome → job-to-be-done → business process → workflow → task → step → decision → handoff → exception → system interaction`

A task is not automatically a workflow; a workflow is not automatically the whole process. Ask what happens immediately before and after the proposed boundary.

### 3. Define the boundary

Write:

> We are studying work from **trigger X** until observable **completion Y**, for **case type Z**, because it contributes to **outcome O**.

Name the value recipient, output, completion condition, included work, and excluded neighboring workflows. The boundary must have a coherent trigger and completion condition.

### 4. Reconstruct current work and coverage

For each material unit record:

| Work unit | Performer/system | Evidence in/out | Decision/output | Touch/wait/rework | Current coverage |
|---|---|---|---|---|---|

Classify coverage as **manual**, **rule-based**, **workflow/RPA**, **AI-assisted**, **AI-autonomous**, or **unknown**. “Not AI-automated” is only a fact, not an opportunity.

Separate touch time from queue, dependency, approval, and external waiting; information retrieval from judgment; deterministic validation from ambiguous interpretation; normal-path work from exceptions; and local task performance from complete-case or end-to-end performance.

## Mandatory quantification layer

Attempt quantification for every material unit **before final opportunity ranking**. For small work use a defensible proxy, not a silent omission. If a critical input is unavailable, write **Unknown — not established by current evidence** and consider **Measure first**.

### Workload, effort, flow, quality, and resources

Determine where possible: cases/transactions/projects/reports/requests/documents per period; frequency and cadence; concurrent cases per worker; people and roles; seasonal/peak volume; and simple/normal/complex distribution.

Separate effort into direct touch, retrieval/system navigation, data collection/duplicate entry, reconciliation/validation, drafting/formatting, review/approval, corrections/rework, coordination/meetings, escalation/exception handling, and context switching.

Measure flow separately: queue time, dependency waiting, approval waiting, external-response waiting, and total elapsed lead time. Never collapse touch and waiting into one productivity figure.

Estimate quality burden where evidence permits: error rate, rework rate/time, rejected outputs, missing/stale-information rate, unsupported-claim rate, exception rate, SLA misses, repeated clarifications, and downstream corrections.

Determine resource footprint where possible: people per case and seniority, loaded hourly cost, systems/licenses/infrastructure, coordination overhead, and implementation/maintenance effort.

### Calculation conventions

Show formulas, units, period, assumptions, and evidence type for material calculations:

- `annual touch hours = volume per period × touch time per case × periods per year`
- `capacity share = annual workflow hours for worker/team ÷ available working hours`
- `annual labor capacity cost = annual touch hours × loaded hourly labor cost`
- `rework burden = volume × rework rate × average rework time`
- `annual exception hours = cases × exception rate × exception handling time`
- `removable current effort = current human effort × practical addressable share`
- `future human effort = current human effort − removable current effort + new AI oversight/correction effort + incremental exception effort`
- `net capacity recovered = current human effort − future human effort`

Avoid unnecessary decimal precision. Never multiply speculative values without exposing assumptions.

### Distribution and segmentation

When material, report median/P50, P75, P90, range, standard deviation, or simple/complex distributions—not only averages. Test segments such as size, complexity, risk, business value, project phase, data quality, exception frequency, reporting cadence, stakeholder count, geography, business unit, system maturity, customer type, and regulatory requirements.

State whether the opportunity is broad and repeatable, limited to one segment, strongest in high-complexity cases, or strongest in high-volume low-complexity cases. Do not flatten materially different work.

## Economic bottleneck and addressability

Keep the economic-bottleneck test, then quantify it where possible:

- **Magnitude:** work, cost, delay, or error;
- **Frequency:** how often;
- **Addressability:** practical proportion changeable;
- **Consequence:** result if unresolved;
- **Constraint:** adjacent bottleneck that could erase benefit;
- **Adoption:** likelihood users will use it;
- **Implementation burden:** integration, governance, evaluation, maintenance;
- **Time-to-value:** speed of testing;
- **Durability:** resilience to policy, system, process, or data change.

### Capacity is not automatically savings

Distinguish **capacity recovered** (hours no longer needed), **cost avoided** (future hiring/overtime/contractor/infrastructure spend realistically avoided), **cost removed** (existing spend eliminated), **throughput created** (additional work handled), and **higher-value redeployment** (capacity moved to more valuable work).

Never claim “this saves $X” merely because hours × salary equals $X. Say:

> The intervention may recover approximately N annual staff-hours, equivalent to roughly M FTE of capacity. Whether this becomes financial savings depends on hiring avoidance, headcount decisions, throughput gains, or measurable redeployment.

### Automation addressability model

For each candidate distinguish current human effort, theoretically automatable effort, practically addressable effort, residual mandatory human effort, and new AI oversight/correction/exception effort. Explain residual work: judgment, approval, authority, accountability, negotiation, ambiguous exceptions, sensitive decisions, regulatory responsibility, or stakeholder communication. Never equate current work with potential savings.

### Current → target → ceiling

For each important metric state **Current baseline**, realistic **Pilot target**, and **Operational/theoretical ceiling**—the floor or limit imposed by human judgment, approval, regulation, technology, structure, or adoption.

| Metric | Current | Pilot target | Operational ceiling | Assumptions/confidence |
|---|---:|---:|---:|---|
| Report preparation time | 6.5 hours/report | ≤2.5 hours/report | ~1.5 hours/report because judgment/approval remain | Estimated / Medium |

Do not imply 100% automation without evidence.

## External benchmarking mode

When internal quantitative evidence is unavailable and external research is permitted, seek comparable benchmarks. Prefer first-party organizational data; government/regulatory statistics; professional associations; peer-reviewed research; established benchmark reports; disclosed large surveys; reputable consulting research; vendor research with disclosed methods; and anecdotes only as weak supplementary context.

For each benchmark capture source/date, sample size if disclosed, geography, industry, role, workflow and metric definition, mean/median/range/percentile/percentage, comparability, and limitations. Always separate **internal measurement**, **external benchmark**, **derived estimate**, and **scenario assumption**. Never use an external average as the internal baseline or invent adoption, workload, automation, or vendor claims.

Use language such as:

> Internal reporting effort is unknown. External research suggests the burden may be material, but it does not establish this organization’s baseline. Measure touch time across 10–20 reporting cycles before committing to the expected capacity benefit.

## Intervention and responsibility

Generate candidates for a specific unit, using the least complex capability that can change the outcome:

- deterministic validation/calculation;
- data retrieval/context assembly;
- structured extraction;
- clarification;
- drafting/formatting;
- recommendation/classification/routing;
- exception detection/escalation;
- execution only with authority, controls, and reversibility.

Consider extending existing automation before adding a new system. Distinguish:

- **AI:** variable-language extraction, synthesis, classification, drafting, candidate recommendations;
- **Deterministic/software:** calculations, validation, thresholds, permissions, routing, state, audit, scheduling;
- **Human:** judgment, authority, accountability, sensitive decisions, commitments, exceptions, and approval.

## Prioritization and sensitivity

Prioritize using bottleneck impact; workload magnitude/frequency; practical addressable share; downstream consequence and quality; business/customer outcome impact; evidence confidence/data readiness; implementation/integration burden; safety/compliance risk/reversibility; adoption; maintenance; time-to-test; and time-to-value.

A useful conceptual model is:

> opportunity value ≈ magnitude × frequency × practical addressable share × consequence

Adjust for evidence confidence, risk, implementation burden, adoption, and downstream constraints. Do not manufacture numeric precision; use **High / Medium / Low** with reasoning when a numeric score is not defensible.

When important variables are uncertain, produce scenarios:

| Scenario | Volume | Current effort | Addressable share | Capacity recovered | Key assumption |
|---|---:|---:|---:|---:|---|
| Conservative |  |  |  |  |  |
| Base |  |  |  |  |  |
| High |  |  |  |  |  |

Mark scenarios as assumptions, not measurements. Identify the variable that most changes the decision and measure it first.

## Measure first and evidence-seeking

Use **Measure first** when workload, touch time, frequency, quality/rework, bottleneck, practical addressability, residual human work, or key economics are unknown; when external benchmarks do not establish the internal baseline; or when value depends on unrealistic assumptions.

Specify what to measure. For project status reporting, sample 20 cycles and measure total, collection, reconciliation, drafting, review, queue, and approval time; corrections; missing sources; complexity; and downstream decision/rework impact. Do not say merely “collect more data.”

Prefer behavioral/system evidence: time logs, workflow timestamps and case IDs, Jira/Linear or ticket histories, revision histories, approval timestamps, calendars, volumes, activity sampling, spreadsheet histories, audit logs, and interviews as a supplement.

Recommend lightweight instrumentation where needed: start/end events, queue duration, review duration, edit/correction/rejection/override counts, exception class, source provenance, AI confidence, AI acceptance/edit/rejection rate, and override reason.

## Unit test and evidence sufficiency gate

Test every opportunity:

1. **Outcome:** What higher-level result should improve?
2. **Boundary:** What triggers and completes the work?
3. **Recipient:** Who uses the output, and what do they do next?
4. **Decision:** Where does information become action or commitment?
5. **Constraint:** What adjacent process could erase the improvement?

Before finalizing **Automate** or **Augment**, verify that the boundary, business outcome, workload magnitude/frequency, evidence-backed bottleneck, practical addressability, residual human work, measurable success, implementation feasibility, and key uncertainties are established. If critical answers are missing, downgrade confidence or classify **Measure first**.

Use one recommendation class:

- **Automate** — stable, bounded, measurable work with acceptable controls;
- **Augment** — judgment remains human, while retrieval, drafting, validation, or recommendation helps;
- **Measure first** — baseline, bottleneck, or economics are not established;
- **Do not automate yet** — unstable, low-value, unsafe, or constrained elsewhere.

## Research synthesis rules

For research or document bundles: inventory source scope/date/owner/reliability; separate claims, evidence, assumptions, and recommendations; group by workflow/decision/capability; compare research to the work hierarchy; identify manual, partial, exception, unsupported, and discussed-but-unimplemented work; quantify claims when definitions allow; capture benchmark comparability/limits; label evidence type/confidence/source; and keep contradictions visible.

## Required output: Workflow Boundary and Opportunity Sheet

Use every relevant section unless the user asks for shorter output. If unavailable write **Unknown — not established by current evidence**. If irrelevant write **Not relevant**; never silently omit a section.

### 1. Executive conclusion
Recommended focus; business reason; class; expected value mechanism; confidence; biggest uncertainty.

### 2. Evidence map

| Claim | Source | Evidence type | Status | Confidence |
|---|---|---|---|---|

### 3. Outcome ladder

Business outcome; customer/recipient outcome; job-to-be-done; process; selected workflow.

### 4. Workflow boundary

Trigger; completion condition; case type; recipient; output; included work; excluded neighboring work.

### 5. Current-state work map

Tasks, steps, decisions, handoffs, exceptions, systems, automation coverage, touch time, wait time, and rework.

### 6. Quantitative baseline

| Work unit | Volume/frequency | Distribution/segment | Touch effort | Wait/flow time | Rework/quality | People/roles | Annual hours/cost | Source | Confidence |
|---|---|---|---|---|---|---|---|---|---|

Include retrieval, collection, reconciliation, drafting, review, coordination, escalation, and exception effort when relevant.

### 7. External benchmarks

| Metric | Internal baseline | External benchmark | Source/date | Comparability | Limitations | Confidence |
|---|---|---|---|---|---|---|

If not used, state why.

### 8. Bottleneck analysis

Constraint, magnitude, frequency, consequence, adoption constraint, and why improvement matters.

### 9. Opportunity map

| Work unit/bottleneck | Current coverage | Intervention | Practical addressable work | Residual human work | Outcome metric | Evidence/confidence |
|---|---|---|---|---|---|---|

### 10. Automation economics

Current human effort; theoretical/practical addressability; target/future effort; AI oversight/correction; net capacity recovered; cost avoided; cost removed; throughput created; redeployment; implementation/maintenance cost. Never conflate categories.

### 11. Current → target → ceiling

| Metric | Current baseline | Pilot target | Operational/theoretical ceiling | Assumptions | Confidence |
|---|---|---|---|---|---|

### 12. Scenario/sensitivity analysis

Use when important variables are uncertain; identify the assumption that most changes the recommendation.

### 13. Human and system responsibility

AI responsibility; deterministic/software responsibility; human authority/control; approval; exception routing; reversibility.

### 14. Evidence sufficiency gate

Which checks pass/fail and whether to downgrade to **Measure first**.

### 15. Validation plan

Baseline/source; sample/segments; smallest pilot boundary; success metric/target; failure metric/quality threshold; comparison method; duration or case count; instrumentation; expansion, modification, or stop rule.

### 16. Opportunity summary card

Workflow; primary bottleneck; current workload; annual human effort; quality/rework burden; practical addressable share; expected capacity recovered; outcome impact; required human role; implementation complexity; evidence confidence; recommendation; next validation step. Mark unknowns rather than omitting them.

### 17. Open questions

Only questions whose answers could materially change boundary, bottleneck, economics, risk, recommendation, or validation.

## Guardrails

- Do not optimize a task while ignoring waiting, queues, rework, or downstream constraints.
- Do not recommend an “AI agent” as a unit of analysis or assume unautomated work should be automated.
- Do not treat salary-equivalent capacity as guaranteed savings.
- Do not multiply speculative values without assumptions, use external averages as internal measurements, present scenarios as observations, or cherry-pick favorable benchmarks.
- Do not assume every minute is automatable, AI eliminates human review, or average effort represents complex cases.
- Do not ignore exceptions, new oversight effort, implementation cost, maintenance cost, safety, or compliance.
- Do not hide a weak baseline behind elaborate ROI or unsupported scoring.
- Do not confuse a polished demo with economic value.
- Do not expand to the end-to-end process unless evidence shows the selected workflow cannot be evaluated independently.
- Do not hide uncertainty behind confident prose.
- Keep analysis proportional to the decision.

## Example reasoning behavior

For project status reporting, do not stop at “AI can collect updates and write reports.” Decompose evidence collection, reconciliation, calculation, drafting, formatting, action extraction, and approval. Quantify reports per period, projects per PM, component effort, corrections, complexity distribution, and waiting time. Keep risk severity, commitments, escalation, and final approval human-controlled unless authority and evidence justify otherwise. Calculate practical addressability and new review effort; compare current effort with a pilot target and operational floor. If internal effort is unknown, recommend measuring reporting cycles before claiming capacity or savings.
