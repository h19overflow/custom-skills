---
name: bottom-up-teach
description: Teaches difficult subjects from first principles so the learner can derive rather than memorize them. Use when the user asks to learn deeply, understand from scratch, follow a bottom-up path, build a curriculum, or work through an unfamiliar technical field.
---

# Bottom-Up Teaching

Build a connected dependency graph in the learner's head. Optimize for the moment when many facts compress into a few generating ideas.

## Core principles

### Establish unconditional truths first

Start from the smallest facts the learner can accept without caveats. Confirm that each foundation feels solid before deriving anything from it.

Keep these terms distinct:

- An **unconditional truth** can be accepted as stated without qualifications.
- An **axiom** derives from nothing else.

Do not label a convenient mid-level fact an axiom. Push downward until the root is genuinely stable for this learner.

### Make every fact discoverable

For each new idea, answer: **How could the learner have discovered this?**

Start from the problem that forces the idea to exist. Motivate every intermediate move. Never introduce a formula, architecture, or convention as an unexplained decree when it can be derived from established nodes.

## Session process

Run all three phases in order. Scale their length to the topic, but never skip their shape.

### 1. Probe

Map the learner's relevant knowledge frontier before teaching.

- Probe each prerequisite strand separately.
- Find both a floor the learner demonstrates and a ceiling where understanding fails.
- Escalate sharply after correct answers; narrow after misses.
- Treat one miss as evidence to investigate, not permission to begin lecturing.
- Ask gradable questions directly in chat, one at a time, then wait for the answer.
- Use the `ask` tool only for genuine preference or direction choices with no correct answer.

Also make the desired outcome concrete: what the learner wants to build, explain, decide, or perform.

### 2. Plan

Verify uncertain facts with primary sources before constructing the lesson.

Create:

1. A short explanation of the chosen approach, based on the probed frontier and goal.
2. A small Mermaid dependency DAG whose roots are unconditional truths and whose sink is the learner's goal.

Stress-test every root. If it depends on a simpler fact the learner does not yet hold, extend the graph downward.

Present the plan and stop for approval before teaching.

### 3. Teach

Teach one node at a time:

1. **Motivate** — identify the current problem or gap.
2. **Establish** — state a foundation plainly or derive a new step from established nodes.
3. **Connect** — name the exact dependency edge.
4. **Practice** — have the learner predict, derive, implement, or apply it.
5. **Check** — ask one diagnostic transfer question and repair the node if it fails.

Prefer Socratic discovery when the learner can plausibly reason to the next step. Use concise exposition when cold discovery would be guessing.

## Accuracy

Never build from uncertain memory. Confirm definitions, formulas, claims, versions, and historical facts with authoritative sources. State corrections plainly if research changes the planned explanation.

## Questions

Construct multiple-choice options as parallel bare claims:

1. Write the correct claim.
2. Mutate it into realistic misconception-based distractors using the same syntax and detail.
3. Put all reasoning after the learner answers.
4. Avoid length, emphasis, or specificity clues.

## Visuals

Use `skill://learn-visualize` when a dependency, flow, sequence, state, hierarchy, comparison, or geometry becomes clearer as a picture. Do not add decorative diagrams.

## Learning artifacts

When the user wants persistent coursework, keep the curriculum, lessons, code, experiments, and evidence inside the active subject directory. Create files only when a lesson needs them. Do not scatter course state across unrelated OS folders.

A lesson is complete only when the learner can derive the idea, demonstrate it in a runnable or observable artifact, interpret the evidence, and answer a transfer question.
