#!/usr/bin/env python3
"""Fail when a shipped Windows binary needs a Visual C++ runtime that is not beside it.

CI runners have the VC++ Redistributable installed, so "it runs on the runner" proves
nothing. On clean Windows the v6.2.0-v6.4.0 desktop exe and the bundled llama-server
both died with STATUS_DLL_NOT_FOUND (found in Windows Sandbox, 2026-11-22).

Static check only: reads PE import tables, executes nothing.

Usage:
    python scripts/check_windows_crt.py <exe-or-dll-or-directory> [...]
"""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

# ucrtbase and api-ms-win-crt-* are part of Windows 10+; these are not.
VC_RUNTIME = re.compile(r"^(vcruntime|msvcp|vcomp|concrt|vccorlib)\d+.*\.dll$", re.IGNORECASE)


def pe_imports(data: bytes) -> list[str]:
    """DLL names from the import table of a PE image."""
    try:
        if data[:2] != b"MZ":
            raise ValueError("not a PE file")
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe : pe + 4] != b"PE\0\0":
            raise ValueError("not a PE file")
        section_count = struct.unpack_from("<H", data, pe + 6)[0]
        optional_size = struct.unpack_from("<H", data, pe + 20)[0]
        optional = pe + 24
        is_64 = struct.unpack_from("<H", data, optional)[0] == 0x20B
        directories = optional + (112 if is_64 else 96)
        import_rva = struct.unpack_from("<I", data, directories + 8)[0]
        sections = [
            struct.unpack_from("<IIII", data, optional + optional_size + 40 * index + 8)
            for index in range(section_count)
        ]

        def offset(rva: int) -> int:
            for virtual_size, address, raw_size, raw in sections:
                if address <= rva < address + max(virtual_size, raw_size):
                    return rva - address + raw
            raise ValueError("import table points outside the image")

        names: list[str] = []
        if not import_rva:
            return names
        position = offset(import_rva)
        while True:
            name_rva = struct.unpack_from("<I", data, position + 12)[0]
            if not name_rva:
                return names
            start = offset(name_rva)
            names.append(data[start : data.index(b"\0", start)].decode("latin-1"))
            position += 20
    except struct.error as exc:
        raise ValueError("truncated PE file") from exc


def check(target: Path) -> list[str]:
    """Problems for one binary, or for every exe/dll directly inside a directory."""
    if target.is_dir():
        binaries = sorted(p for p in target.iterdir() if p.suffix.lower() in {".exe", ".dll"})
    elif target.is_file():
        binaries = [target]
    else:
        return [f"{target}: not found"]
    if not binaries:
        return [f"{target}: no Windows binaries to check"]
    problems: list[str] = []
    for binary in binaries:
        try:
            imports = pe_imports(binary.read_bytes())
        except ValueError as exc:
            problems.append(f"{binary}: {exc}")
            continue
        beside = {p.name.lower() for p in binary.parent.iterdir()}
        for name in imports:
            if VC_RUNTIME.match(name) and name.lower() not in beside:
                problems.append(
                    f"{binary.name} imports {name}, which clean Windows does not have and is not shipped beside it"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="+", type=Path)
    args = parser.parse_args()
    problems = [problem for target in args.targets for problem in check(target)]
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        return 1
    print(f"Visual C++ runtime check passed: {', '.join(str(t) for t in args.targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
