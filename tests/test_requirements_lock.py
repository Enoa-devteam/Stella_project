"""requirements-platform.lock must satisfy every specifier in requirements.txt.

CI installs from the lock, so a floor raised in requirements.txt without re-locking
is never exercised (pycryptodomex 3.24.2 floor vs 3.24.1 locked, issue #182).
"""

from __future__ import annotations

from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def _requirements(path: Path) -> list[Requirement]:
    reqs = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        reqs.append(Requirement(line))
    return reqs


def _locked_versions(path: Path) -> dict[str, Version]:
    pins: dict[str, Version] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        pins[canonicalize_name(name.split("[", 1)[0])] = Version(version.strip())
    return pins


def test_platform_lock_satisfies_requirements_txt():
    pins = _locked_versions(ROOT / "requirements-platform.lock")
    sources = [ROOT / "requirements.txt", ROOT / "requirements-platform.in"]
    problems = []
    for source in sources:
        for req in _requirements(source):
            name = canonicalize_name(req.name)
            if name not in pins:
                problems.append(f"{source.name}: {req} is not in requirements-platform.lock")
            elif not req.specifier.contains(pins[name], prereleases=True):
                problems.append(f"{source.name}: {req} but lock pins {name}=={pins[name]}")
    assert not problems, "re-lock with uv pip compile (see lock header):\n" + "\n".join(problems)
