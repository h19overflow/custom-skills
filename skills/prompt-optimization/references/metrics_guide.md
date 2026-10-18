# DSPy Metrics Guide

## Overview

Metrics in DSPy are functions that evaluate how well a prediction matches the expected output. They determine:
1. Which bootstrapped examples to keep during optimization
2. How to score different prompt configurations
3. Final evaluation scores for comparison

## Metric Function Signature

```python
def metric(example, prediction, trace=None) -> bool | float:
    """
    Evaluate a prediction against an expected example.

    Args:
        example: The input example with expected outputs (dspy.Example)
        prediction: The model's output (dspy.Prediction)
        trace: Optional trace information for debugging

    Returns:
        bool: True/False for pass/fail metrics
        float: 0.0-1.0 for continuous scoring metrics
    """
    pass
```

## Built-in Metrics

### Exact Match

```python
def exact_match(example, prediction, trace=None) -> bool:
    """Strict equality check."""
    return prediction.answer.strip().lower() == example.answer.strip().lower()
```

### Contains Match

```python
def contains_match(example, prediction, trace=None) -> bool:
    """Check if expected answer is contained in prediction."""
    return example.answer.strip().lower() in prediction.answer.strip().lower()
```

### F1 Score (Token-level)

```python
def f1_score(example, prediction, trace=None) -> float:
    """Token-level F1 score."""
    pred_tokens = set(prediction.answer.lower().split())
    gold_tokens = set(example.answer.lower().split())

    if not pred_tokens or not gold_tokens:
        return 0.0

    precision = len(pred_tokens & gold_tokens) / len(pred_tokens)
    recall = len(pred_tokens & gold_tokens) / len(gold_tokens)

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)
```

## Custom Metrics

### Multi-Field Matching

```python
def multi_field_exact(example, prediction, trace=None) -> bool:
    """Check multiple fields for exact match."""
    fields_to_check = ["name", "date", "amount"]

    for field in fields_to_check:
        expected = getattr(example, field, "").strip().lower()
        predicted = getattr(prediction, field, "").strip().lower()
        if expected != predicted:
            return False

    return True
```

### Weighted Multi-Criteria

```python
def weighted_metric(example, prediction, trace=None) -> float:
    """
    Score based on multiple weighted criteria.

    Weights:
    - Correctness: 50%
    - Format compliance: 30%
    - Conciseness: 20%
    """
    score = 0.0

    # Correctness (50%)
    if example.answer.strip().lower() in prediction.answer.strip().lower():
        score += 0.5

    # Format compliance (30%)
    if prediction.answer.startswith("Answer:"):
        score += 0.3

    # Conciseness (20%)
    if len(prediction.answer) < 200:
        score += 0.2

    return score
```

### Regex-Based Validation

```python
import re

def regex_metric(example, prediction, trace=None) -> bool:
    """Validate output against expected pattern."""
    # Example: validating date format
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    if not re.search(date_pattern, prediction.date):
        return False

    return prediction.date == example.date
```

### Semantic Similarity

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Initialize once (outside metric function)
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def semantic_similarity(example, prediction, trace=None) -> float:
    """Score based on embedding similarity."""
    model = get_embedding_model()

    expected_emb = model.encode(example.answer)
    predicted_emb = model.encode(prediction.answer)

    # Cosine similarity
    similarity = np.dot(expected_emb, predicted_emb) / (
        np.linalg.norm(expected_emb) * np.linalg.norm(predicted_emb)
    )

    return float(max(0, similarity))  # Clamp to [0, 1]
```

### LLM-as-Judge

```python
import dspy

class JudgeSignature(dspy.Signature):
    """Evaluate if the prediction correctly answers the question."""

    question: str = dspy.InputField()
    expected_answer: str = dspy.InputField()
    predicted_answer: str = dspy.InputField()
    is_correct: bool = dspy.OutputField(desc="True if prediction is semantically equivalent to expected")
    confidence: float = dspy.OutputField(desc="Confidence score 0-1")

_judge = None

def get_judge():
    global _judge
    if _judge is None:
        _judge = dspy.Predict(JudgeSignature)
    return _judge

def llm_judge_metric(example, prediction, trace=None) -> float:
    """Use LLM to judge semantic equivalence."""
    judge = get_judge()

    result = judge(
        question=example.question,
        expected_answer=example.answer,
        predicted_answer=prediction.answer
    )

    if result.is_correct:
        return result.confidence
    return 0.0
```

## Composite Metrics

### All-or-Nothing

```python
def all_criteria_metric(example, prediction, trace=None) -> bool:
    """All criteria must pass."""
    checks = [
        len(prediction.answer) > 0,                    # Non-empty
        example.answer.lower() in prediction.answer.lower(),  # Contains expected
        len(prediction.answer) < 500,                  # Not too long
        not prediction.answer.startswith("I don't")   # No refusals
    ]
    return all(checks)
```

### Graduated Scoring

```python
def graduated_metric(example, prediction, trace=None) -> float:
    """Partial credit based on how many criteria pass."""
    score = 0.0
    total_criteria = 4

    # Criterion 1: Non-empty
    if len(prediction.answer.strip()) > 0:
        score += 1

    # Criterion 2: Contains expected
    if example.answer.lower() in prediction.answer.lower():
        score += 1

    # Criterion 3: Reasonable length
    if 10 < len(prediction.answer) < 500:
        score += 1

    # Criterion 4: No obvious errors
    if "error" not in prediction.answer.lower():
        score += 1

    return score / total_criteria
```

## Metrics for Specific Tasks

### Classification

```python
def classification_metric(example, prediction, trace=None) -> bool:
    """Exact match for classification labels."""
    valid_labels = {"positive", "negative", "neutral"}

    predicted_label = prediction.label.strip().lower()
    expected_label = example.label.strip().lower()

    # Reject invalid predictions
    if predicted_label not in valid_labels:
        return False

    return predicted_label == expected_label
```

### Extraction

```python
import json

def extraction_metric(example, prediction, trace=None) -> float:
    """Score extracted entities against expected."""
    try:
        expected_entities = set(json.loads(example.entities))
        predicted_entities = set(json.loads(prediction.entities))
    except json.JSONDecodeError:
        return 0.0

    if not expected_entities:
        return 1.0 if not predicted_entities else 0.0

    # F1-style scoring
    true_positives = len(expected_entities & predicted_entities)
    precision = true_positives / len(predicted_entities) if predicted_entities else 0
    recall = true_positives / len(expected_entities)

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)
```

### Summarization

```python
def summarization_metric(example, prediction, trace=None) -> float:
    """
    Score summaries based on:
    - Key point coverage
    - Appropriate length
    - No hallucinations (heuristic)
    """
    score = 0.0

    # Key point coverage (using keyword matching as proxy)
    key_terms = example.key_points.lower().split(",")
    summary_lower = prediction.summary.lower()
    covered = sum(1 for term in key_terms if term.strip() in summary_lower)
    coverage_score = covered / len(key_terms) if key_terms else 0
    score += 0.5 * coverage_score

    # Length appropriateness (25-100 words ideal)
    word_count = len(prediction.summary.split())
    if 25 <= word_count <= 100:
        score += 0.3
    elif 10 <= word_count <= 150:
        score += 0.15

    # Basic hallucination check (no numbers not in source)
    import re
    source_numbers = set(re.findall(r'\d+', example.source))
    summary_numbers = set(re.findall(r'\d+', prediction.summary))
    if summary_numbers.issubset(source_numbers):
        score += 0.2

    return score
```

### Code Generation

```python
def code_metric(example, prediction, trace=None) -> float:
    """
    Evaluate generated code.
    Note: Actual execution should be sandboxed!
    """
    score = 0.0

    code = prediction.code.strip()

    # Basic syntax check (Python)
    try:
        compile(code, '<string>', 'exec')
        score += 0.3  # Syntactically valid
    except SyntaxError:
        return 0.0

    # Contains expected function/class
    if example.function_name in code:
        score += 0.2

    # Has docstring
    if '"""' in code or "'''" in code:
        score += 0.1

    # Has type hints
    if "->" in code or ": " in code:
        score += 0.1

    # Approximate logic check (keyword-based)
    expected_keywords = example.expected_keywords.split(",")
    for kw in expected_keywords:
        if kw.strip() in code:
            score += 0.3 / len(expected_keywords)

    return min(score, 1.0)
```

## Best Practices

### 1. Start Simple

Begin with exact match or contains match. Add complexity only if needed.

### 2. Handle Edge Cases

```python
def robust_metric(example, prediction, trace=None) -> bool:
    # Guard against None/empty
    if not prediction or not hasattr(prediction, 'answer'):
        return False

    pred_answer = getattr(prediction, 'answer', '') or ''
    exp_answer = getattr(example, 'answer', '') or ''

    return pred_answer.strip().lower() == exp_answer.strip().lower()
```

### 3. Log Failures During Development

```python
def debug_metric(example, prediction, trace=None) -> bool:
    result = prediction.answer.strip().lower() == example.answer.strip().lower()

    if not result:
        print(f"MISMATCH:")
        print(f"  Expected: {example.answer}")
        print(f"  Got: {prediction.answer}")

    return result
```

### 4. Cache Expensive Operations

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text: str):
    """Cache embeddings for repeated texts."""
    return model.encode(text)
```

### 5. Normalize Before Comparing

```python
import re

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text

def normalized_match(example, prediction, trace=None) -> bool:
    return normalize_text(prediction.answer) == normalize_text(example.answer)
```

## Metric Selection Guide

| Task Type | Recommended Metric |
|-----------|-------------------|
| Q&A (factual) | Exact match or contains |
| Q&A (open-ended) | Semantic similarity or LLM judge |
| Classification | Exact match on label |
| Entity extraction | F1 on entities |
| Summarization | Composite (coverage + length + factuality) |
| Code generation | Syntax validity + functional tests |
| Translation | BLEU or semantic similarity |
