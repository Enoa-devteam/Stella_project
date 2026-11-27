# CI

[中文](ci.md) | English · [Documentation](../README.en.md)

`.github/workflows/ci.yml` defines these jobs:

| Job | Contents |
|---|---|
| `lint` | `ruff check .` (Python 3.11) |
| `memory-benchmark-public` | Depends on `lint`: runs the retrieval benchmark on public PersonaMem data; `--gate` fails the job below threshold |
| `security` | `pip-audit -r requirements.txt` (blocking; no advisory is ignored) + `bandit` (non-blocking; report uploaded as an artifact) |
| `test` | 3.10 / 3.11 / 3.12 version matrix; installs base and optional platform bridge dependencies from `requirements-platform.lock`, runs `pytest tests/ --cov=. --cov-branch -n auto`, and uploads coverage as an artifact |
| `cli` | The Rust CLI (`cli/`): `cargo fmt --check` + `clippy -- -D warnings` + `cargo test`, plus a help-text smoke test over the subcommand list (doctor/init/start/stop/restart/status/logs/upgrade/migrate/plugin/capabilities/manifest/compose) so refactors cannot silently drop commands |
| `rust-crates` | windows-latest matrix: `cargo test --locked` for `desktop/src-tauri`, `stella-installer/src-tauri`, `desktop/launcher`, `runtime-manager` and `memory_rust/native`, plus `scripts/check_rust_msrv.py` to confirm each declared `rust-version` covers the locked dependencies (crates without a `rust-version` are skipped; currently `desktop/src-tauri`, `stella-installer/src-tauri`, and `desktop/launcher` declare none) (#182: CI used to compile only `cli`, so dependency API breaks surfaced at release time). The desktop shell gets a placeholder `desktop/dashboard-dist` so `generate_context!()` compiles |
| `windows-native` | Runs `pytest tests/windows` on windows-latest — the native matrix for process trees, upgrades, and installation reliability (sentinels/PIDs/activation records depend on real Windows semantics) |
| `documentation` | Stdlib link/anchor, language-pair, redirect, state checks and six positive/negative contract tests |
| `flow-manifest` | Source anchor and generated message-flow drift gate |
| `flow-closure` | GitNexus index plus inventory/discovered-entry reconciliation |
| `notify` | PRs only: summarize status and comment (depends on test/lint/security/cli/rust-crates/flow-manifest/flow-closure/documentation/memory-benchmark-public) |

`test` depends on `lint` and `security` passing; `fail-fast: false` ensures the other versions continue when one fails. Older workflows on the same branch are cancelled automatically.

**Reproduce the CI environment locally**:

```bash
pip install -r requirements-platform.lock -r requirements-dev.txt pytest pytest-asyncio pytest-cov pytest-xdist pytest-timeout
ruff check .
pytest tests/ --cov=. --cov-branch -n auto --dist loadgroup --timeout=120 --timeout-method=thread
```

`requirements-platform.lock` includes the base dependencies from `requirements.txt` (the only adapter is `nonebot-adapter-onebot`, shared by OneBot V11/V12; other catalog adapters are short-circuited in core, see [#134](https://github.com/Enoa-devteam/stella_project/issues/134)) plus optional Uninfo from `requirements-platform.in`. Alconna, required by the OneBot v11 outbound target codec, is also a base dependency.

`pip-audit` is blocking and currently ignores no advisory: the three `cryptography` exemptions once kept for the NoneBot QQ adapter were removed together with the non-OneBot adapters (see the comment in `.github/workflows/ci.yml`); reassess them if that adapter returns.

**When only 3.10 is red and every test is a collect error, suspect a transitive dependency first.** The direct dependencies in `requirements.txt` are mostly lower bounds (`>=`) and transitive ones are not pinned at all, so any upstream release that supports 3.11+ only turns `test (3.10)` completely red while 3.11 / 3.12 and the dev machine stay green. The 2026-09-01 instance: `pygtrie` 2.6.0 used `typing.Self` (3.11+) at module top level, so `import nonebot` raised `AttributeError: module 'typing' has no attribute 'Self'` and all 622 tests errored. Triage by reading **only the first traceback in the `==== ERRORS ====` section** (the tens of thousands of log lines are all copies of the same one); the fix is to pin that transitive dependency explicitly in `requirements.txt` with the reason written down.

Dashboard tests/build are defined separately in `.github/workflows/dashboard_ci.yml`. Agent bootstrap modes and additional gates are in [verification](../agent/verification.md).
