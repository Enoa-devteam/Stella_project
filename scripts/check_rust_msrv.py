#!/usr/bin/env python3
"""Fail when a crate's declared ``rust-version`` is below what its locked dependencies need.

Dependabot can lock a dependency whose own ``rust-version`` is newer than the crate's
(sha2 0.11.1 needs 1.88 while memory_rust/native declared 1.75, issue #182). Nothing
fails on CI because CI builds with stable, so the declared MSRV quietly becomes false.

Reads ``cargo metadata --locked`` only; compiles nothing.

Usage:
    python scripts/check_rust_msrv.py <crate-dir> [...]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_version(text: str) -> tuple[int, ...]:
    parts = [int(p) for p in text.strip().split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def check_metadata(metadata: dict) -> list[str]:
    """Problems for each workspace member whose rust-version is below a locked dependency's."""
    members = set(metadata["workspace_members"])
    packages = metadata["packages"]
    deps = [p for p in packages if p["id"] not in members and p.get("rust_version")]
    problems = []
    for pkg in packages:
        if pkg["id"] not in members:
            continue
        declared = pkg.get("rust_version")
        if not declared:
            continue  # no MSRV claimed, nothing to keep honest
        too_new = [d for d in deps if parse_version(d["rust_version"]) > parse_version(declared)]
        if too_new:
            worst = max(too_new, key=lambda d: parse_version(d["rust_version"]))
            names = ", ".join(sorted({f"{d['name']} {d['version']} ({d['rust_version']})" for d in too_new}))
            problems.append(
                f"{pkg['name']}: rust-version {declared} < {worst['rust_version']} required by {names}"
            )
    return problems


def crate_metadata(crate_dir: Path) -> dict:
    out = subprocess.run(
        ["cargo", "metadata", "--locked", "--format-version", "1"],
        cwd=crate_dir,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    return json.loads(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("crates", nargs="+", type=Path)
    args = parser.parse_args(argv)
    failed = False
    for crate in args.crates:
        problems = check_metadata(crate_metadata(crate))
        for problem in problems:
            print(f"::error::{crate}: {problem}")
        if problems:
            failed = True
        else:
            print(f"ok {crate}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
