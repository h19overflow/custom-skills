#!/usr/bin/env python3
"""Cross-platform installer for custom skills into various agent harnesses."""

import argparse
import shutil
import sys
from pathlib import Path

TARGET_PATHS = {
    "omp": Path("~/.omp/agent/managed-skills").expanduser(),
    "omp-user": Path("~/.omp/skills").expanduser(),
    "claude": Path("~/.claude/skills").expanduser(),
    "codex": Path("~/.codex/skills").expanduser(),
    "cursor": Path("~/.cursor/skills").expanduser(),
    "gemini": Path("~/.gemini/skills").expanduser(),
    "agents": Path("~/.agents/skills").expanduser(),
}

def install_skills(target_dir: Path, source_dir: Path, skill_names=None, force=False):
    target_dir.mkdir(parents=True, exist_ok=True)
    installed, skipped = 0, 0
    
    for item in sorted(source_dir.iterdir()):
        if not item.is_dir():
            continue
        if skill_names and item.name not in skill_names:
            continue
            
        dest = target_dir / item.name
        if dest.exists():
            if not force:
                print(f"[-] Skipped (already exists): {item.name}")
                skipped += 1
                continue
            shutil.rmtree(dest)
            
        shutil.copytree(item, dest)
        print(f"[+] Installed: {item.name} -> {dest}")
        installed += 1
        
    print(f"\nDone: {installed} installed, {skipped} skipped into {target_dir}")

def main():
    parser = argparse.ArgumentParser(description="Install custom agent skills safely.")
    parser.add_argument(
        "--target", "-t",
        choices=list(TARGET_PATHS.keys()) + ["all-detected"],
        default="omp",
        help="Target agent harness directory (default: omp)"
    )
    parser.add_argument(
        "--custom-path",
        type=Path,
        help="Custom destination directory path"
    )
    parser.add_argument(
        "--skill", "-s",
        action="append",
        dest="skills",
        help="Specific skill name(s) to install (default: all skills)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing skills at destination"
    )
    
    args = parser.parse_args()
    root_dir = Path(__file__).resolve().parent
    source_dir = root_dir / "skills"
    
    if not source_dir.exists():
        print(f"Error: skills directory not found at {source_dir}", file=sys.stderr)
        sys.exit(1)
        
    if args.custom_path:
        dest_dir = args.custom_path.expanduser()
        install_skills(dest_dir, source_dir, args.skills, args.force)
    elif args.target == "all-detected":
        detected = [k for k, p in TARGET_PATHS.items() if p.parent.exists()]
        if not detected:
            print("No agent root directories detected. Use --target <name> or --custom-path.")
            sys.exit(1)
        for t in detected:
            print(f"\n--- Installing to detected target: {t} ({TARGET_PATHS[t]}) ---")
            install_skills(TARGET_PATHS[t], source_dir, args.skills, args.force)
    else:
        dest_dir = TARGET_PATHS[args.target]
        install_skills(dest_dir, source_dir, args.skills, args.force)

if __name__ == "__main__":
    main()
