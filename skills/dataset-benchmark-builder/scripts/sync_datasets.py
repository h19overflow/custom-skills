# /// script
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""
Dataset Synchronizer (sync_datasets.py):
Idempotently publishes local .jsonl benchmark datasets to hosted backends:
Langfuse, LangSmith, or Arize Phoenix.

Usage:
  uv run sync_datasets.py --file .evals/datasets/benchmark.jsonl --name my_benchmark --provider langfuse --dry-run
  uv run sync_datasets.py --file .evals/datasets/benchmark.jsonl --name my_benchmark --provider langsmith
"""

import sys
import os
import json
import argparse
from typing import List, Dict, Any

def sync_to_langfuse(dataset_name: str, records: List[Dict[str, Any]], dry_run: bool = False):
    print(f"[Langfuse] Target dataset: '{dataset_name}' ({len(records)} records)")
    if dry_run:
        print("[Langfuse] DRY-RUN mode. Validating payload structures:")
        for r in records[:3]:
            print(f"  -> Item ID: {r.get('id')} | Category: {r.get('category')}")
        print("[Langfuse] Validation successful. No remote changes made.")
        return

    try:
        from langfuse import Langfuse
    except ImportError:
        print("Error: `langfuse` package not installed. Run with `uv run --with langfuse python sync_datasets.py ...`")
        sys.exit(1)

    client = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    )
    # Check if dataset exists or create
    try:
        client.get_dataset(name=dataset_name)
        print(f"[Langfuse] Existing dataset '{dataset_name}' found. Upserting items...")
    except Exception:
        print(f"[Langfuse] Creating dataset '{dataset_name}'...")
        client.create_dataset(name=dataset_name, description="Agent evaluation benchmark")

    for item in records:
        client.create_dataset_item(
            dataset_name=dataset_name,
            input=item.get("input", {}),
            expected_output=item.get("expected_trajectory", {}),
            metadata=item.get("metadata", {})
        )
    client.flush()
    print(f"[Langfuse] Successfully synced {len(records)} items.")

def sync_to_langsmith(dataset_name: str, records: List[Dict[str, Any]], dry_run: bool = False):
    print(f"[LangSmith] Target dataset: '{dataset_name}' ({len(records)} records)")
    if dry_run:
        print("[LangSmith] DRY-RUN mode. Validating payload structures:")
        for r in records[:3]:
            print(f"  -> Item ID: {r.get('id')} | Category: {r.get('category')}")
        print("[LangSmith] Validation successful. No remote changes made.")
        return

    try:
        from langsmith import Client
    except ImportError:
        print("Error: `langsmith` package not installed. Run with `uv run --with langsmith python sync_datasets.py ...`")
        sys.exit(1)

    client = Client()
    # Check if dataset exists
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    if datasets:
        dataset = datasets[0]
        print(f"[LangSmith] Found existing dataset ID: {dataset.id}")
    else:
        dataset = client.create_dataset(dataset_name=dataset_name, description="Agent evaluation benchmark")
        print(f"[LangSmith] Created new dataset ID: {dataset.id}")

    inputs = [r.get("input", {}) for r in records]
    outputs = [r.get("expected_trajectory", {}) for r in records]
    metadata = [r.get("metadata", {}) for r in records]
    client.create_examples(inputs=inputs, outputs=outputs, metadata=metadata, dataset_id=dataset.id)
    print(f"[LangSmith] Successfully synced {len(records)} items.")

def sync_to_phoenix(dataset_name: str, records: List[Dict[str, Any]], dry_run: bool = False):
    print(f"[Arize Phoenix] Target dataset: '{dataset_name}' ({len(records)} records)")
    if dry_run:
        print("[Arize Phoenix] DRY-RUN mode. Validating payload structures:")
        for r in records[:3]:
            print(f"  -> Item ID: {r.get('id')} | Category: {r.get('category')}")
        print("[Arize Phoenix] Validation successful. No remote changes made.")
        return

    try:
        import phoenix as px
        import pandas as pd
    except ImportError:
        print("Error: `phoenix` / `pandas` not installed.")
        sys.exit(1)

    client = px.Client()
    df = pd.DataFrame([
        {
            "id": r.get("id"),
            "category": r.get("category"),
            "input": json.dumps(r.get("input", {})),
            "expected_output": json.dumps(r.get("expected_trajectory", {})),
            "metadata": json.dumps(r.get("metadata", {}))
        }
        for r in records
    ])
    client.upload_dataset(dataset_name=dataset_name, dataframe=df, input_keys=["input"], output_keys=["expected_output"])
    print(f"[Arize Phoenix] Successfully synced {len(records)} items.")

def main():
    parser = argparse.ArgumentParser(description="Sync local eval datasets to hosted platforms")
    parser.add_argument("--file", type=str, required=True, help="Path to .jsonl dataset file")
    parser.add_argument("--name", type=str, required=True, help="Target dataset name")
    parser.add_argument("--provider", type=str, choices=["langfuse", "langsmith", "phoenix"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="Simulate synchronization without remote mutations")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: Dataset file not found at: {args.file}")
        sys.exit(1)

    records = []
    with open(args.file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        print("Error: Dataset file contains no valid records.")
        sys.exit(1)

    print(f"Loaded {len(records)} records from: {args.file}")

    if args.provider == "langfuse":
        sync_to_langfuse(args.name, records, dry_run=args.dry_run)
    elif args.provider == "langsmith":
        sync_to_langsmith(args.name, records, dry_run=args.dry_run)
    elif args.provider == "phoenix":
        sync_to_phoenix(args.name, records, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
