"""scripts/check_rust_msrv.py: declared rust-version must cover locked dependencies."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_rust_msrv.py"
spec = importlib.util.spec_from_file_location("check_rust_msrv", SCRIPT)
assert spec and spec.loader
check_rust_msrv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_rust_msrv)


def _metadata(declared: str | None, deps: dict[str, str | None]) -> dict:
    packages = [{"id": "me", "name": "me", "version": "1.0.0", "rust_version": declared}]
    packages += [
        {"id": name, "name": name, "version": "0.1.0", "rust_version": rv} for name, rv in deps.items()
    ]
    return {"workspace_members": ["me"], "packages": packages}


def test_dependency_newer_than_declared_msrv_is_reported():
    problems = check_rust_msrv.check_metadata(_metadata("1.75", {"sha2": "1.88", "syn": "1.71"}))
    assert len(problems) == 1
    assert "1.75 < 1.88" in problems[0]
    assert "sha2" in problems[0]
    assert "syn" not in problems[0]


def test_msrv_covering_all_dependencies_passes():
    assert check_rust_msrv.check_metadata(_metadata("1.88", {"sha2": "1.88", "x": None})) == []


def test_versions_compare_numerically_not_lexically():
    assert check_rust_msrv.check_metadata(_metadata("1.9", {"a": "1.10"}))
    assert check_rust_msrv.check_metadata(_metadata("1.85.0", {"a": "1.85"})) == []


def test_crate_without_declared_msrv_is_skipped():
    assert check_rust_msrv.check_metadata(_metadata(None, {"sha2": "1.88"})) == []
