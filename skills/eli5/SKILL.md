---
name: eli5
description: Explains unfamiliar or confusing topics in very simple language without losing correctness. This skill should be used when the user says "ELI5," "explain like I am 5," "I don't understand," "I am confused," "make it simpler," or asks for a beginner-friendly breakdown.
---

# ELI5

## Goal

Turn a confusing explanation into a small, concrete mental model. Assume no prior knowledge of the topic, but never talk down to the user.

## Method

1. Start with one plain sentence stating what the thing is or does.
2. Use one familiar analogy when it makes the idea clearer.
3. Name the important pieces and give each piece one simple job.
4. Trace one concrete example from beginning to end.
5. End with a one-sentence recap.

## Rules

- Prefer everyday words and short sentences.
- Introduce one new idea at a time.
- Replace jargon with plain language. When a technical term is necessary, define it immediately.
- Explain who starts an action, what happens next, and what result comes back.
- Keep examples tiny and directly related to the user's question.
- For code, show only the lines needed to demonstrate the flow. Explain what calls what, the input, and the output.
- Use arrows or a short numbered list for multi-step flows.
- Preserve important safety, security, money, and data-loss details. Put necessary caveats under `Important exception:` rather than hiding them.
- Avoid baby talk, fake quotes, excessive metaphors, and unexplained technical terms.
- Do not add advanced details unless they are required for the basic explanation or the user asks for them.
- Do not ask the user to choose an explanation style when enough context already exists. Pick the clearest simple explanation and proceed.

## Response Shape

Use this shape when it fits:

```text
Simple idea: ...

Think of it like: ...

What happens:
1. ...
2. ...
3. ...

Tiny example:
...

In one sentence: ...
```

Adapt the shape instead of forcing sections that add no value.
