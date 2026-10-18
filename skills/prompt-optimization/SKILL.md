---
name: prompt-optimization
description: This skill implements the DSPy eval-optimize-eval workflow for systematically optimizing LLM prompts. Use when the user wants to improve prompt performance through data-driven optimization, create few-shot demonstrations, or generate production-ready prompts for integration with LangChain or other frameworks. The skill outputs exportable prompts (instructions + few-shot demos) as the final deliverable, not DSPy-specific saved files.
---

# Prompt Optimization

## Overview

This skill implements a systematic prompt optimization workflow using DSPy's compilation and evaluation capabilities. The primary deliverable is a set of optimized prompts (instructions + few-shot demonstrations) ready for integration into production systems like LangChain, not DSPy-specific artifacts.

## Workflow Decision Tree

```
START
  |
  v
Do you have evaluation data?
  |
  +-- NO --> Step 1: Create Evaluation Dataset
  |
  +-- YES
        |
        v
      Do you have a baseline metric?
        |
        +-- NO --> Step 2: Baseline Evaluation
        |
        +-- YES
              |
              v
            Ready for optimization --> Step 3: Optimize
              |
              v
            Step 4: Post-Optimization Evaluation
              |
              v
            Step 5: Export Optimized Prompts
```

## Step 1: Create Evaluation Dataset

### Minimum Requirements

- At least 20 examples for meaningful optimization (50+ recommended)
- Split: 70% train, 15% dev, 15% test
- Each example needs input fields and expected output

### Dataset Format

```python
import dspy

# Define the example structure
examples = [
    dspy.Example(
        question="What is the capital of France?",
        answer="Paris"
    ).with_inputs("question"),
    # ... more examples
]

# Split the dataset
train_set = examples[:int(len(examples) * 0.7)]
dev_set = examples[int(len(examples) * 0.7):int(len(examples) * 0.85)]
test_set = examples[int(len(examples) * 0.85):]
```

### Loading from Files

```python
import json
import dspy

def load_examples_from_jsonl(filepath: str, input_keys: list[str]) -> list[dspy.Example]:
    """Load examples from JSONL file."""
    examples = []
    with open(filepath, 'r') as f:
        for line in f:
            data = json.loads(line)
            example = dspy.Example(**data).with_inputs(*input_keys)
            examples.append(example)
    return examples
```

## Step 2: Baseline Evaluation

### Configure the LLM

```python
import dspy

# Configure the language model
lm = dspy.LM(
    model="openai/gpt-4o-mini",  # or anthropic/Codex-3-haiku, etc.
    api_key="your-api-key"
)
dspy.configure(lm=lm)
```

### Define the Signature

```python
class QuestionAnswer(dspy.Signature):
    """Answer questions accurately and concisely."""

    question: str = dspy.InputField(desc="The question to answer")
    answer: str = dspy.OutputField(desc="A concise, accurate answer")
```

### Create Baseline Module

```python
# Simple zero-shot baseline
baseline_module = dspy.Predict(QuestionAnswer)

# Or with chain-of-thought reasoning
baseline_module = dspy.ChainOfThought(QuestionAnswer)
```

### Define Metrics

```python
def exact_match(example, prediction, trace=None) -> bool:
    """Check if prediction matches expected answer exactly."""
    return prediction.answer.strip().lower() == example.answer.strip().lower()

def semantic_similarity(example, prediction, trace=None) -> float:
    """Score based on semantic similarity (0-1 scale)."""
    # Use embedding similarity or LLM-as-judge
    # Return float between 0 and 1
    pass

def composite_metric(example, prediction, trace=None) -> float:
    """Combine multiple metrics."""
    accuracy = exact_match(example, prediction, trace)
    # Add other factors: length, format compliance, etc.
    return float(accuracy)
```

### Run Baseline Evaluation

```python
from dspy.evaluate import Evaluate

evaluator = Evaluate(
    devset=dev_set,
    metric=exact_match,
    num_threads=4,
    display_progress=True,
    display_table=5  # Show 5 example results
)

baseline_score = evaluator(baseline_module)
print(f"Baseline Score: {baseline_score:.2%}")
```

## Step 3: Optimize

### Choose an Optimizer

| Optimizer | Best For | Training Examples | Notes |
|-----------|----------|-------------------|-------|
| `BootstrapFewShot` | Few-shot learning | 10-50 | Fast, generates demos |
| `BootstrapFewShotWithRandomSearch` | Better few-shot | 20-100 | Tries multiple demo sets |
| `MIPROv2` | Instruction + demos | 50-200 | Optimizes both instructions and examples |
| `COPRO` | Instruction only | 20-100 | Focuses on instruction tuning |

### BootstrapFewShot (Recommended Starting Point)

```python
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(
    metric=exact_match,
    max_bootstrapped_demos=4,  # Number of few-shot examples
    max_labeled_demos=4,       # Max from labeled training data
    max_rounds=1               # Bootstrap iterations
)

optimized_module = optimizer.compile(
    student=dspy.Predict(QuestionAnswer),
    trainset=train_set
)
```

### MIPROv2 (For Instruction + Demo Optimization)

```python
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2(
    metric=exact_match,
    num_candidates=10,     # Instruction candidates to try
    init_temperature=1.0,  # Creativity in instruction generation
    verbose=True
)

optimized_module = optimizer.compile(
    student=dspy.Predict(QuestionAnswer),
    trainset=train_set,
    num_batches=20,        # Optimization iterations
    max_bootstrapped_demos=3,
    max_labeled_demos=4
)
```

### BootstrapFewShotWithRandomSearch (Balanced Option)

```python
from dspy.teleprompt import BootstrapFewShotWithRandomSearch

optimizer = BootstrapFewShotWithRandomSearch(
    metric=exact_match,
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
    num_candidate_programs=8,  # Number of demo sets to try
    num_threads=4
)

optimized_module = optimizer.compile(
    student=dspy.Predict(QuestionAnswer),
    trainset=train_set
)
```

## Step 4: Post-Optimization Evaluation

### Evaluate on Dev Set

```python
optimized_score = evaluator(optimized_module)
print(f"Optimized Score: {optimized_score:.2%}")
print(f"Improvement: {(optimized_score - baseline_score):.2%}")
```

### Final Evaluation on Test Set

```python
test_evaluator = Evaluate(
    devset=test_set,
    metric=exact_match,
    num_threads=4,
    display_progress=True
)

final_score = test_evaluator(optimized_module)
print(f"Final Test Score: {final_score:.2%}")
```

### Compare Results

```python
print("\n=== Optimization Results ===")
print(f"Baseline (dev):   {baseline_score:.2%}")
print(f"Optimized (dev):  {optimized_score:.2%}")
print(f"Final (test):     {final_score:.2%}")
print(f"Improvement:      {(final_score - baseline_score):.2%}")
```

## Step 5: Export Optimized Prompts

This is the critical step for production integration. The optimized prompts must be exported in a format usable by LangChain or other frameworks. Use `scripts/extract_prompts.py` for extraction and `scripts/optimize_and_export.py` for the complete pipeline.

### Quick Export

```python
from extract_prompts import export_optimized_prompts

result = export_optimized_prompts(
    optimized_module=optimized_module,
    output_dir="./optimized_prompts",
    name="my_task"
)

# Result contains paths to:
# - my_task.json: Raw extracted data
# - my_task_langchain.py: Ready-to-use LangChain code
# - my_task_prompt.txt: Human-readable format
```

### Output Files

1. **JSON Export** (`{name}.json`): Contains raw instructions and demos for custom integrations
2. **LangChain Code** (`{name}_langchain.py`): Ready-to-run LangChain implementation
3. **Human-Readable** (`{name}_prompt.txt`): Documentation and review format

## Common Issues and Solutions

### Issue: Empty Demos After Optimization

```python
# Check if demos were created
if not optimized_module.demos:
    print("No demos bootstrapped. Try:")
    print("1. Increase max_bootstrapped_demos")
    print("2. Use more training examples")
    print("3. Relax the metric threshold")
```

### Issue: Low Optimization Improvement

- Increase training set size (aim for 50+ examples)
- Try MIPROv2 for instruction optimization
- Check if metric is too strict
- Verify training data quality

### Issue: Extracting from ChainOfThought

```python
# ChainOfThought wraps the predictor
if hasattr(optimized_module, 'predict'):
    actual_predictor = optimized_module.predict
    demos = actual_predictor.demos
else:
    demos = optimized_module.demos
```

## Resources

### scripts/

- `optimize_and_export.py` - Complete optimization pipeline with LangChain export
- `extract_prompts.py` - Standalone prompt extraction utility

### references/

- `dspy_optimizers.md` - Detailed optimizer comparison and configuration guide
- `metrics_guide.md` - Guide to writing effective evaluation metrics
