# Core Custom Engineering & Systems Skills

This archive contains **exclusively the custom-authored engineering, architecture, systems thinking, and agent evaluation suites** from this workstation.

All other skill classes have been removed:
- Excluded: Knowledge & workflow notes (OS workspace)
- Excluded: Project-specific skills (Burhan reports, FluxType, Job Radar, etc.)
- Excluded: Bespoke UI & design skills (brutalist UI, styling prompts, web design)
- Excluded: Third-party vendor plugins (Codex marketplace, stock video tools)

---

## Overview

- **Total Core Engineering Skills**: 50
- **Categorization**:
  1. `01-architecture-and-systems`: 13 skills (OMP managed)
  2. `02-agent-eval-and-frameworks`: 37 skills (Canonical agent engineering suite)

---

## Directory Layout

```
custom-skills/
├── README.md                          # Architecture guide & skill index
├── INVENTORY.csv                      # Full tabular index with descriptions & paths
├── MANIFEST.json                      # Machine-readable JSON database
│
├── by-category/
│   ├── 01-architecture-and-systems/   # Systems thinking, complexity review, failure semantics
│   └── 02-agent-eval-and-frameworks/  # 6-phase evaluation lifecycle & Deep Agents/LangChain
│
└── skills/                            # Flat library of all 50 skills (ready to drop into any agent)
    ├── <skill-name>/
    └── ...
```

---

## Detailed Skill Manifest

### 01-architecture-and-systems (13 skills)
`agent-architecture-patterns`, `ai-opportunity-boundary`, `complexity-review`, `exception-design`, `graphify`, `leverage-point-identification`, `module-boundary-design`, `shared-information-design` ... and 5 more
### 02-agent-eval-and-frameworks (37 skills)
`bottom-up-teach`, `ci-eval-runner`, `dataset-benchmark-builder`, `deep-agents-core`, `deep-agents-memory`, `deep-agents-orchestration`, `deepagents-python-quickstart`, `deepagents-typescript-quickstart` ... and 29 more


---

## Suite Highlights

### 1. Architecture, Systems Thinking & Software Design
- `complexity-review`: John Ousterhout complexity analysis, information hiding, interface depth.
- `exception-design`: Failure semantics, idempotency, retries, and error aggregation.
- `module-boundary-design`: Deep modules, boundary justification, concept budgeting.
- `shared-information-design`: Shared invariants, protocol centralization, single-owner policies.
- `split-or-join-functions`: Function boundary independence vs cohesion decisions.
- `graphify`: Codebase knowledge graph, call-path tracing, architectural queries.
- `systems-thinking-analyst`: Feedback loops, delays, systemic traps, and high-leverage points.
- `leverage-point-identification`: Places to intervene in complex systems.
- `system-trap-identification`: Structural matches to archetype system traps.
- `agent-architecture-patterns`: Multi-agent architectural design patterns.
- `ai-opportunity-boundary`: Boundary discovery, ROI, and evaluation framing.
- `windows-secure-env-handoff`: Process environment persistence & handoff on Windows.
- `windows-startup-cleanup`: Windows standalone startup script sanitation.

### 2. 6-Phase Agent Evaluation Framework
- `eval-contract-definer`: Formalizes tool schemas, DAG transitions, and token budgets.
- `eval-scorer-builder`: Deterministic code assertions, trajectory linters, agent judges.
- `dataset-benchmark-builder`: 4-slice benchmark datasets, adversarial generation.
- `ci-eval-runner`: CI/CD regression gating, summary JSON, and GitHub PR comments.
- `trace-observability-integrator`: W3C traceparent context propagation for MCP and OTel.
- `trace-feedback-miner`: Closed-loop trace mining into regression fixtures.
- `hosted-eval-provisioner`: Langfuse, LangSmith, and Arize provisioner.
- `langsmith-online-eval-engineering`: Live online evaluators.
- `eval-engineering`: Agent repository inspection, verifiers, Harbor runs.

### 3. Deep Agents & Agent Frameworks
- `deep-agents-core`: Core harness, configuration, SKILL.md for Deep Agents.
- `deep-agents-memory`: Persistent/ephemeral store and filesystem access.
- `deep-agents-orchestration`: Subagent task planning and HITL interrupts.
- `deepagents-python-quickstart`: Scaffold minimal Python Deep Agent.
- `deepagents-typescript-quickstart`: Scaffold minimal TypeScript Deep Agent.
- `managed-deep-agents`: Build, test, and deploy MDA agents.
- `ecosystem-primer`: Decision framework for LangChain / LangGraph / Deep Agents.
- `microsoft-foundry`: Foundry agents and models engineering.
- `langchain-*`: dependencies, fundamentals, middleware, quickstart, rag.
- `langgraph-*`: cli, fundamentals, human-in-the-loop, persistence, quickstarts.
- `langfuse`: Tracing, observability, prompt/eval/dataset workflows.
- `prompt-optimization`: DSPy eval-optimize-eval loop.
- `skill-creator`: Creating, optimizing, and testing agent skills.
- `swarm`: Parallel independent task dispatching.

---

## Installation on Any Device

### 1. Automated Safe Installation (`install.py`)

Clone the repository and run the zero-dependency installer:

```bash
git clone https://github.com/h19overflow/custom-skills.git
cd custom-skills

# Install all skills into OMP managed-skills (default)
python install.py --target omp

# Install all skills into Claude Code
python install.py --target claude

# Install into Codex, Cursor, Gemini, or all detected agents
python install.py --target codex
python install.py --target cursor
python install.py --target gemini
python install.py --target all-detected

# Install specific skills only
python install.py --target omp --skill complexity-review --skill exception-design
```

### 2. Manual Installation

- **OMP**: Copy any skill into `~/.omp/agent/managed-skills/<name>` or `~/.omp/skills/<name>`.
- **Claude Code**: Copy into `~/.claude/skills/<name>` or link to `~/.agents/skills/<name>`.
- **Codex**: Copy into `~/.codex/skills/<name>`.
- **Cursor / Gemini**: Copy into `~/.cursor/skills/<name>` or `~/.gemini/skills/<name>`.
