#!/usr/bin/env python3
"""
Complete DSPy Optimization Pipeline with LangChain Export

This script implements the full eval→optimize→eval workflow and exports
optimized prompts (instructions + few-shot demos) for LangChain integration.

Usage:
    python optimize_and_export.py --data examples.jsonl --output ./optimized
    python optimize_and_export.py --data examples.jsonl --optimizer mipro --output ./optimized
"""

import argparse
import json
from pathlib import Path
from typing import Callable

import dspy
from dspy.evaluate import Evaluate
from dspy.teleprompt import (
    BootstrapFewShot,
    BootstrapFewShotWithRandomSearch,
    MIPROv2,
)

from extract_prompts import export_optimized_prompts


def load_examples_from_jsonl(
    filepath: str,
    input_keys: list[str],
    output_keys: list[str]
) -> list[dspy.Example]:
    """Load examples from JSONL file."""
    examples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                example = dspy.Example(**data).with_inputs(*input_keys)
                examples.append(example)
    return examples


def split_dataset(
    examples: list[dspy.Example],
    train_ratio: float = 0.7,
    dev_ratio: float = 0.15
) -> tuple[list, list, list]:
    """Split examples into train, dev, and test sets."""
    n = len(examples)
    train_end = int(n * train_ratio)
    dev_end = int(n * (train_ratio + dev_ratio))

    return examples[:train_end], examples[train_end:dev_end], examples[dev_end:]


def create_exact_match_metric(output_field: str) -> Callable:
    """Create an exact match metric for a specific output field."""
    def exact_match(example, prediction, trace=None) -> bool:
        expected = getattr(example, output_field, "").strip().lower()
        predicted = getattr(prediction, output_field, "").strip().lower()
        return expected == predicted
    return exact_match


def create_contains_metric(output_field: str) -> Callable:
    """Create a contains metric (prediction contains expected)."""
    def contains_match(example, prediction, trace=None) -> bool:
        expected = getattr(example, output_field, "").strip().lower()
        predicted = getattr(prediction, output_field, "").strip().lower()
        return expected in predicted
    return contains_match


def create_signature_from_fields(
    input_fields: list[str],
    output_fields: list[str],
    instructions: str = ""
) -> type:
    """Dynamically create a DSPy Signature class."""
    field_definitions = {}

    for field in input_fields:
        field_definitions[field] = dspy.InputField()

    for field in output_fields:
        field_definitions[field] = dspy.OutputField()

    signature_class = type(
        "DynamicSignature",
        (dspy.Signature,),
        {"__doc__": instructions, **field_definitions}
    )

    return signature_class


def run_baseline_evaluation(
    module: dspy.Module,
    dev_set: list[dspy.Example],
    metric: Callable,
    num_threads: int = 4
) -> float:
    """Run baseline evaluation and return score."""
    evaluator = Evaluate(
        devset=dev_set,
        metric=metric,
        num_threads=num_threads,
        display_progress=True,
        display_table=5
    )

    score = evaluator(module)
    return score


def optimize_with_bootstrap(
    signature: type,
    train_set: list[dspy.Example],
    metric: Callable,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 4
) -> dspy.Module:
    """Optimize using BootstrapFewShot."""
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        max_rounds=1
    )

    optimized = optimizer.compile(
        student=dspy.Predict(signature),
        trainset=train_set
    )

    return optimized


def optimize_with_random_search(
    signature: type,
    train_set: list[dspy.Example],
    metric: Callable,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 4,
    num_candidate_programs: int = 8,
    num_threads: int = 4
) -> dspy.Module:
    """Optimize using BootstrapFewShotWithRandomSearch."""
    optimizer = BootstrapFewShotWithRandomSearch(
        metric=metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        num_candidate_programs=num_candidate_programs,
        num_threads=num_threads
    )

    optimized = optimizer.compile(
        student=dspy.Predict(signature),
        trainset=train_set
    )

    return optimized


def optimize_with_mipro(
    signature: type,
    train_set: list[dspy.Example],
    metric: Callable,
    num_candidates: int = 10,
    num_batches: int = 20,
    max_bootstrapped_demos: int = 3,
    max_labeled_demos: int = 4
) -> dspy.Module:
    """Optimize using MIPROv2 (instruction + demo optimization)."""
    optimizer = MIPROv2(
        metric=metric,
        num_candidates=num_candidates,
        init_temperature=1.0,
        verbose=True
    )

    optimized = optimizer.compile(
        student=dspy.Predict(signature),
        trainset=train_set,
        num_batches=num_batches,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos
    )

    return optimized


def run_optimization_pipeline(
    data_path: str,
    output_dir: str,
    input_fields: list[str],
    output_fields: list[str],
    model: str = "openai/gpt-4o-mini",
    api_key: str | None = None,
    optimizer_type: str = "bootstrap",
    instructions: str = "",
    metric_type: str = "exact",
    name: str = "optimized_prompt"
) -> dict:
    """
    Run the complete optimization pipeline.

    Args:
        data_path: Path to JSONL file with examples
        output_dir: Directory for output files
        input_fields: List of input field names
        output_fields: List of output field names
        model: LLM model identifier
        api_key: API key for the LLM
        optimizer_type: One of 'bootstrap', 'random_search', 'mipro'
        instructions: Task instructions for the signature
        metric_type: One of 'exact', 'contains'
        name: Name for output files

    Returns:
        Dictionary with scores and export paths
    """
    # Configure LLM
    lm_kwargs = {"model": model}
    if api_key:
        lm_kwargs["api_key"] = api_key

    lm = dspy.LM(**lm_kwargs)
    dspy.configure(lm=lm)

    # Load and split data
    print(f"\n{'='*60}")
    print("LOADING DATA")
    print('='*60)
    examples = load_examples_from_jsonl(data_path, input_fields, output_fields)
    print(f"Loaded {len(examples)} examples")

    train_set, dev_set, test_set = split_dataset(examples)
    print(f"Train: {len(train_set)}, Dev: {len(dev_set)}, Test: {len(test_set)}")

    # Create signature and metric
    signature = create_signature_from_fields(input_fields, output_fields, instructions)

    if metric_type == "exact":
        metric = create_exact_match_metric(output_fields[0])
    else:
        metric = create_contains_metric(output_fields[0])

    # Baseline evaluation
    print(f"\n{'='*60}")
    print("BASELINE EVALUATION")
    print('='*60)
    baseline_module = dspy.Predict(signature)
    baseline_score = run_baseline_evaluation(baseline_module, dev_set, metric)
    print(f"Baseline Score: {baseline_score:.2%}")

    # Optimization
    print(f"\n{'='*60}")
    print(f"OPTIMIZATION ({optimizer_type.upper()})")
    print('='*60)

    if optimizer_type == "bootstrap":
        optimized_module = optimize_with_bootstrap(signature, train_set, metric)
    elif optimizer_type == "random_search":
        optimized_module = optimize_with_random_search(signature, train_set, metric)
    elif optimizer_type == "mipro":
        optimized_module = optimize_with_mipro(signature, train_set, metric)
    else:
        raise ValueError(f"Unknown optimizer: {optimizer_type}")

    # Post-optimization evaluation on dev set
    print(f"\n{'='*60}")
    print("POST-OPTIMIZATION EVALUATION (Dev Set)")
    print('='*60)
    optimized_score = run_baseline_evaluation(optimized_module, dev_set, metric)
    print(f"Optimized Score: {optimized_score:.2%}")
    print(f"Improvement: {(optimized_score - baseline_score):.2%}")

    # Final evaluation on test set
    print(f"\n{'='*60}")
    print("FINAL EVALUATION (Test Set)")
    print('='*60)
    final_score = run_baseline_evaluation(optimized_module, test_set, metric)
    print(f"Final Test Score: {final_score:.2%}")

    # Export optimized prompts
    print(f"\n{'='*60}")
    print("EXPORTING OPTIMIZED PROMPTS")
    print('='*60)
    export_result = export_optimized_prompts(
        optimized_module=optimized_module,
        output_dir=output_dir,
        name=name
    )

    # Summary
    print(f"\n{'='*60}")
    print("OPTIMIZATION SUMMARY")
    print('='*60)
    print(f"Baseline (dev):   {baseline_score:.2%}")
    print(f"Optimized (dev):  {optimized_score:.2%}")
    print(f"Final (test):     {final_score:.2%}")
    print(f"Total Improvement: {(final_score - baseline_score):.2%}")
    print(f"\nExported files:")
    print(f"  - {export_result['json_path']}")
    print(f"  - {export_result['langchain_path']}")
    print(f"  - {export_result['prompt_path']}")

    return {
        "baseline_score": baseline_score,
        "optimized_score": optimized_score,
        "final_score": final_score,
        "improvement": final_score - baseline_score,
        "export_paths": {
            "json": export_result['json_path'],
            "langchain": export_result['langchain_path'],
            "prompt": export_result['prompt_path']
        },
        "extracted": export_result['extracted'],
        "langchain_format": export_result['langchain_format']
    }


def main():
    parser = argparse.ArgumentParser(
        description="DSPy Prompt Optimization Pipeline with LangChain Export"
    )
    parser.add_argument(
        "--data", required=True,
        help="Path to JSONL file with examples"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output directory for exported prompts"
    )
    parser.add_argument(
        "--input-fields", nargs="+", default=["question"],
        help="Input field names (default: question)"
    )
    parser.add_argument(
        "--output-fields", nargs="+", default=["answer"],
        help="Output field names (default: answer)"
    )
    parser.add_argument(
        "--model", default="openai/gpt-4o-mini",
        help="LLM model identifier (default: openai/gpt-4o-mini)"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API key (or set via environment variable)"
    )
    parser.add_argument(
        "--optimizer", choices=["bootstrap", "random_search", "mipro"],
        default="bootstrap",
        help="Optimizer type (default: bootstrap)"
    )
    parser.add_argument(
        "--metric", choices=["exact", "contains"],
        default="exact",
        help="Metric type (default: exact)"
    )
    parser.add_argument(
        "--instructions", default="",
        help="Task instructions for the prompt"
    )
    parser.add_argument(
        "--name", default="optimized_prompt",
        help="Name for output files (default: optimized_prompt)"
    )

    args = parser.parse_args()

    result = run_optimization_pipeline(
        data_path=args.data,
        output_dir=args.output,
        input_fields=args.input_fields,
        output_fields=args.output_fields,
        model=args.model,
        api_key=args.api_key,
        optimizer_type=args.optimizer,
        instructions=args.instructions,
        metric_type=args.metric,
        name=args.name
    )

    print(f"\nOptimization complete!")
    print(f"Final improvement: {result['improvement']:.2%}")


if __name__ == "__main__":
    main()
