#!/usr/bin/env python3
"""
Prompt Extraction Utility for DSPy Optimized Modules

Extracts optimized instructions and few-shot demonstrations from DSPy modules
and formats them for LangChain integration.

Usage:
    # From Python
    from extract_prompts import export_optimized_prompts
    result = export_optimized_prompts(optimized_module, "./output", "my_prompt")

    # Standalone (with saved DSPy module)
    python extract_prompts.py --module saved_module.json --output ./prompts
"""

import argparse
import json
from pathlib import Path
from typing import Any


def extract_optimized_prompt(optimized_module: Any) -> dict:
    """
    Extract the optimized instructions and few-shot demos from a DSPy module.

    Args:
        optimized_module: A compiled DSPy module (Predict, ChainOfThought, etc.)

    Returns:
        Dictionary with:
        - instructions: The optimized system/task instructions
        - demos: List of few-shot demonstration examples
        - signature_info: Original signature metadata
    """
    result = {
        "instructions": "",
        "demos": [],
        "signature_info": {}
    }

    # Get the predictor (handles both Predict and ChainOfThought)
    predictor = optimized_module
    if hasattr(optimized_module, 'predict'):
        predictor = optimized_module.predict

    # Extract signature information
    if hasattr(predictor, 'signature'):
        sig = predictor.signature
        instructions = ""

        # Try different ways to get instructions
        if hasattr(sig, 'instructions'):
            instructions = sig.instructions
        elif hasattr(sig, '__doc__') and sig.__doc__:
            instructions = sig.__doc__

        input_fields = []
        output_fields = []

        if hasattr(sig, 'input_fields'):
            input_fields = list(sig.input_fields.keys())
        if hasattr(sig, 'output_fields'):
            output_fields = list(sig.output_fields.keys())

        result["signature_info"] = {
            "instructions": instructions,
            "input_fields": input_fields,
            "output_fields": output_fields
        }
        result["instructions"] = instructions

    # Extract few-shot demonstrations
    if hasattr(predictor, 'demos') and predictor.demos:
        for demo in predictor.demos:
            demo_dict = _example_to_dict(demo)
            if demo_dict:
                result["demos"].append(demo_dict)

    return result


def _example_to_dict(example: Any) -> dict:
    """Convert a DSPy Example to a dictionary."""
    demo_dict = {}

    # Try different ways to convert Example to dict
    if hasattr(example, '_store'):
        demo_dict = dict(example._store)
    elif hasattr(example, 'toDict'):
        demo_dict = example.toDict()
    elif hasattr(example, '__dict__'):
        demo_dict = {
            k: v for k, v in example.__dict__.items()
            if not k.startswith('_')
        }
    else:
        # Fallback: iterate over attributes
        for attr in dir(example):
            if not attr.startswith('_') and not callable(getattr(example, attr)):
                demo_dict[attr] = getattr(example, attr)

    return demo_dict


def format_prompt_for_langchain(extracted: dict) -> dict:
    """
    Format extracted DSPy prompt for LangChain integration.

    Args:
        extracted: Output from extract_optimized_prompt()

    Returns:
        Dictionary with:
        - system_message: System prompt with instructions
        - few_shot_examples: Formatted examples for FewShotPromptTemplate
        - example_template: Template for formatting each example
        - input_variables: List of input field names
        - output_variables: List of output field names
    """
    # Build system message
    system_message = extracted["instructions"]

    # Get field information
    input_fields = extracted["signature_info"].get("input_fields", [])
    output_fields = extracted["signature_info"].get("output_fields", [])

    # Format few-shot examples
    few_shot_examples = []
    for demo in extracted["demos"]:
        example = {}
        for field in input_fields:
            if field in demo:
                example[field] = demo[field]
        for field in output_fields:
            if field in demo:
                example[field] = demo[field]
        few_shot_examples.append(example)

    # Generate example template
    example_parts = []
    for field in input_fields:
        label = field.replace('_', ' ').title()
        example_parts.append(f"{label}: {{{field}}}")
    for field in output_fields:
        label = field.replace('_', ' ').title()
        example_parts.append(f"{label}: {{{field}}}")

    example_template = "\n".join(example_parts)

    return {
        "system_message": system_message,
        "few_shot_examples": few_shot_examples,
        "example_template": example_template,
        "input_variables": input_fields,
        "output_variables": output_fields
    }


def generate_langchain_code(langchain_format: dict) -> str:
    """
    Generate ready-to-use LangChain code.

    Args:
        langchain_format: Output from format_prompt_for_langchain()

    Returns:
        Python code string ready for use with LangChain
    """
    examples_str = json.dumps(langchain_format["few_shot_examples"], indent=4)
    input_vars = langchain_format["input_variables"]
    output_vars = langchain_format["output_variables"]
    all_vars = input_vars + output_vars

    # Create suffix template (just input fields for the actual query)
    suffix_parts = []
    for field in input_vars:
        label = field.replace('_', ' ').title()
        suffix_parts.append(f"{label}: {{{field}}}")
    for field in output_vars:
        label = field.replace('_', ' ').title()
        suffix_parts.append(f"{label}:")
    suffix_template = "\\n".join(suffix_parts)

    code = f'''"""
LangChain Integration for Optimized Prompt
Generated by DSPy prompt-optimization skill

This file contains the optimized prompt (instructions + few-shot demos)
extracted from DSPy optimization and formatted for LangChain.
"""

from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI  # or: from langchain_anthropic import ChatAnthropic


# =============================================================================
# OPTIMIZED PROMPT COMPONENTS
# =============================================================================

# System instructions (optimized by DSPy)
SYSTEM_INSTRUCTIONS = """{langchain_format["system_message"]}"""

# Few-shot examples (selected by DSPy optimization)
FEW_SHOT_EXAMPLES = {examples_str}

# Example formatting template
EXAMPLE_TEMPLATE = """{langchain_format["example_template"]}"""


# =============================================================================
# LANGCHAIN PROMPT TEMPLATE
# =============================================================================

# Build the example prompt template
example_prompt = PromptTemplate(
    input_variables={all_vars},
    template=EXAMPLE_TEMPLATE
)

# Build the few-shot prompt template
few_shot_prompt = FewShotPromptTemplate(
    examples=FEW_SHOT_EXAMPLES,
    example_prompt=example_prompt,
    prefix=SYSTEM_INSTRUCTIONS,
    suffix="{suffix_template}",
    input_variables={input_vars}
)


# =============================================================================
# USAGE
# =============================================================================

def create_chain(model: str = "gpt-4o-mini", temperature: float = 0.0):
    """Create a LangChain chain with the optimized prompt."""
    llm = ChatOpenAI(model=model, temperature=temperature)
    chain = few_shot_prompt | llm
    return chain


def run_optimized_prompt(**inputs) -> str:
    """
    Run the optimized prompt with given inputs.

    Example:
        result = run_optimized_prompt(question="What is the capital of France?")
    """
    chain = create_chain()
    response = chain.invoke(inputs)
    return response.content


# Example usage
if __name__ == "__main__":
    # Example: run with sample input
    # result = run_optimized_prompt({input_vars[0] if input_vars else "input"}="your input here")
    # print(result)

    # Print the formatted prompt for inspection
    sample_input = {{{repr(input_vars[0]) if input_vars else '"input"'}: "example input"}}
    print("Formatted prompt:")
    print("-" * 60)
    print(few_shot_prompt.format(**sample_input))
'''
    return code


def generate_human_readable(extracted: dict) -> str:
    """Generate a human-readable prompt format."""
    lines = []
    lines.append("=" * 60)
    lines.append("OPTIMIZED PROMPT")
    lines.append("=" * 60)
    lines.append("")

    lines.append("INSTRUCTIONS:")
    lines.append("-" * 40)
    lines.append(extracted["instructions"] or "(No instructions)")
    lines.append("")

    lines.append("FEW-SHOT EXAMPLES:")
    lines.append("-" * 40)

    if extracted["demos"]:
        for i, demo in enumerate(extracted["demos"], 1):
            lines.append(f"\nExample {i}:")
            for key, value in demo.items():
                # Truncate long values for readability
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                lines.append(f"  {key}: {value_str}")
    else:
        lines.append("(No few-shot examples)")

    lines.append("")
    lines.append("=" * 60)
    lines.append("SIGNATURE INFO:")
    lines.append("-" * 40)
    lines.append(f"Input fields: {extracted['signature_info'].get('input_fields', [])}")
    lines.append(f"Output fields: {extracted['signature_info'].get('output_fields', [])}")
    lines.append("=" * 60)

    return "\n".join(lines)


def export_optimized_prompts(
    optimized_module: Any,
    output_dir: str,
    name: str = "optimized_prompt"
) -> dict:
    """
    Export optimized prompts to files for production use.

    Creates:
    - {name}.json: Raw extracted data
    - {name}_langchain.py: Ready-to-use LangChain code
    - {name}_prompt.txt: Human-readable prompt format

    Args:
        optimized_module: Compiled DSPy module
        output_dir: Directory for output files
        name: Base name for output files

    Returns:
        Dictionary with paths and extracted data
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract prompt data
    extracted = extract_optimized_prompt(optimized_module)
    langchain_format = format_prompt_for_langchain(extracted)

    # Save JSON data
    json_path = output_path / f"{name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "extracted": extracted,
            "langchain_format": langchain_format
        }, f, indent=2, default=str)
    print(f"Saved: {json_path}")

    # Save LangChain code
    langchain_path = output_path / f"{name}_langchain.py"
    langchain_code = generate_langchain_code(langchain_format)
    with open(langchain_path, 'w', encoding='utf-8') as f:
        f.write(langchain_code)
    print(f"Saved: {langchain_path}")

    # Save human-readable format
    prompt_path = output_path / f"{name}_prompt.txt"
    human_readable = generate_human_readable(extracted)
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(human_readable)
    print(f"Saved: {prompt_path}")

    return {
        "json_path": str(json_path),
        "langchain_path": str(langchain_path),
        "prompt_path": str(prompt_path),
        "extracted": extracted,
        "langchain_format": langchain_format
    }


def main():
    """CLI entrypoint for extracting prompts from saved DSPy modules."""
    parser = argparse.ArgumentParser(
        description="Extract optimized prompts from DSPy modules"
    )
    parser.add_argument(
        "--module", required=True,
        help="Path to saved DSPy module (JSON)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output directory for exported prompts"
    )
    parser.add_argument(
        "--name", default="optimized_prompt",
        help="Name for output files (default: optimized_prompt)"
    )

    args = parser.parse_args()

    # Load saved module
    # Note: This assumes the module was saved with dspy.save()
    # For custom saved formats, modify the loading logic
    import dspy
    module = dspy.load(args.module)

    result = export_optimized_prompts(
        optimized_module=module,
        output_dir=args.output,
        name=args.name
    )

    print(f"\nExtraction complete!")
    print(f"Files saved to: {args.output}")


if __name__ == "__main__":
    main()
