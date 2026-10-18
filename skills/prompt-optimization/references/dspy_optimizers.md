# DSPy Optimizers Reference Guide

## Overview

DSPy optimizers (also called "teleprompters") automatically tune prompts by:
1. Generating few-shot demonstrations from training data
2. Optimizing instructions through search
3. Selecting the best-performing prompt configuration

## Optimizer Comparison

| Optimizer | What It Optimizes | Speed | Best For |
|-----------|-------------------|-------|----------|
| BootstrapFewShot | Demos only | Fast | Quick optimization, small datasets |
| BootstrapFewShotWithRandomSearch | Demos (multiple candidates) | Medium | Better demo selection |
| MIPROv2 | Instructions + Demos | Slow | Maximum performance, large datasets |
| COPRO | Instructions only | Medium | When demos aren't helpful |

## BootstrapFewShot

The simplest and fastest optimizer. Generates few-shot demonstrations by running the LLM on training examples and keeping successful outputs.

### How It Works

1. For each training example, runs the student module
2. Checks if the output passes the metric
3. Keeps successful (input, output) pairs as demonstrations
4. Adds demonstrations to the prompt

### Configuration

```python
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(
    metric=your_metric,           # Required: evaluation function
    max_bootstrapped_demos=4,     # Max demos to generate
    max_labeled_demos=4,          # Max demos from labeled data
    max_rounds=1,                 # Bootstrap iterations
    max_errors=5                  # Max errors before stopping
)
```

### Parameters Explained

- **metric**: Function(example, prediction, trace) -> bool/float
- **max_bootstrapped_demos**: How many demos to generate via bootstrapping
- **max_labeled_demos**: How many demos to use from labeled training data
- **max_rounds**: How many times to iterate the bootstrap process
- **max_errors**: Stop if this many examples fail during bootstrapping

### When to Use

- You have 10-50 training examples
- You want fast iteration
- Demo selection is more important than instruction tuning

## BootstrapFewShotWithRandomSearch

Extends BootstrapFewShot by trying multiple demo configurations and selecting the best.

### How It Works

1. Generates multiple candidate demo sets
2. Evaluates each on a validation set
3. Selects the best-performing configuration

### Configuration

```python
from dspy.teleprompt import BootstrapFewShotWithRandomSearch

optimizer = BootstrapFewShotWithRandomSearch(
    metric=your_metric,
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
    num_candidate_programs=8,     # Number of demo sets to try
    num_threads=4                 # Parallel evaluation threads
)
```

### When to Use

- You have 20-100 training examples
- You want better demo selection than basic bootstrap
- You have compute budget for multiple evaluations

## MIPROv2

The most powerful optimizer. Optimizes both instructions and demonstrations using a gradient-free search.

### How It Works

1. Generates candidate instruction variations
2. Bootstraps demonstrations for each
3. Evaluates combinations on validation set
4. Uses Bayesian optimization to search the space

### Configuration

```python
from dspy.teleprompt import MIPROv2

optimizer = MIPROv2(
    metric=your_metric,
    num_candidates=10,            # Instruction candidates to generate
    init_temperature=1.0,         # Creativity in instruction generation
    verbose=True                  # Show optimization progress
)

optimized = optimizer.compile(
    student=your_module,
    trainset=train_set,
    num_batches=20,               # Optimization iterations
    max_bootstrapped_demos=3,
    max_labeled_demos=4,
    eval_kwargs={
        "num_threads": 4,
        "display_progress": True
    }
)
```

### Parameters Explained

- **num_candidates**: How many instruction variations to try
- **init_temperature**: Higher = more creative instructions (0.5-1.5 range)
- **num_batches**: Optimization steps (more = better but slower)
- **verbose**: Whether to print progress

### When to Use

- You have 50+ training examples
- You need maximum performance
- You have time for longer optimization

## COPRO

Focuses on instruction optimization without changing demonstrations.

### Configuration

```python
from dspy.teleprompt import COPRO

optimizer = COPRO(
    metric=your_metric,
    breadth=10,                   # Instruction candidates per round
    depth=3,                      # Optimization rounds
    init_temperature=1.0
)

optimized = optimizer.compile(
    student=your_module,
    trainset=train_set,
    eval_kwargs={"num_threads": 4}
)
```

### When to Use

- When few-shot demos don't help (short outputs, simple tasks)
- When instruction clarity is the bottleneck
- When you want faster than MIPROv2 but better than bootstrap

## Choosing an Optimizer

### Decision Tree

```
Training examples < 20?
  YES → BootstrapFewShot (or collect more data)
  NO
    |
    v
Is instruction quality critical?
  YES → MIPROv2 (50+ examples) or COPRO (20+ examples)
  NO
    |
    v
Do you have compute budget for search?
  YES → BootstrapFewShotWithRandomSearch
  NO → BootstrapFewShot
```

### Performance vs Speed Tradeoff

```
Speed:    BootstrapFewShot > COPRO > RandomSearch > MIPROv2
Quality:  MIPROv2 > RandomSearch > COPRO > BootstrapFewShot
```

## Common Configuration Patterns

### Quick Iteration

```python
# Fastest possible optimization
optimizer = BootstrapFewShot(
    metric=metric,
    max_bootstrapped_demos=2,
    max_labeled_demos=2
)
```

### Production Quality

```python
# Best results for production
optimizer = MIPROv2(
    metric=metric,
    num_candidates=15,
    init_temperature=0.8,
    verbose=True
)

optimized = optimizer.compile(
    student=module,
    trainset=train_set,
    num_batches=30,
    max_bootstrapped_demos=4,
    max_labeled_demos=4
)
```

### Instruction-Heavy Tasks

```python
# When clear instructions matter most
optimizer = COPRO(
    metric=metric,
    breadth=15,
    depth=4,
    init_temperature=0.7
)
```

## Troubleshooting

### Problem: No demos generated

**Symptoms**: `optimized_module.demos` is empty

**Solutions**:
1. Lower the metric threshold (make it easier to pass)
2. Increase `max_rounds` in BootstrapFewShot
3. Provide more training examples
4. Check if the metric function is correct

### Problem: Optimization doesn't improve performance

**Symptoms**: Optimized score similar to baseline

**Solutions**:
1. Try MIPROv2 instead of BootstrapFewShot
2. Increase training set size
3. Improve training data quality
4. Check if the task is learnable from demonstrations

### Problem: Optimization takes too long

**Symptoms**: Hours of optimization time

**Solutions**:
1. Reduce `num_candidates` or `num_batches` in MIPROv2
2. Use BootstrapFewShotWithRandomSearch instead
3. Reduce `num_candidate_programs`
4. Use a faster/cheaper LLM for optimization

### Problem: Inconsistent results

**Symptoms**: Different scores on each run

**Solutions**:
1. Set `temperature=0` on the LLM
2. Use more training examples
3. Increase `num_candidate_programs` for better selection
4. Run optimization multiple times and keep best
