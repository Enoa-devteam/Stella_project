# stella v6.4.0

This release builds on [v6.3.0](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.3.0).

**Read Breaking Changes before upgrading.** The memory database migrates from schema 22 to 24, NapCat is no longer bundled, and only the OneBot V11 adapter is installed.

## Breaking Changes

- **Memory schema 22 → 24**, migrated automatically on first start, with an `agent_memory.db.pre-v24-<timestamp>.bak` backup beside the database. v6.3.0 does not refuse a schema 24 database, so do not simply run the old version on it: to roll back, stop stella and restore the backup. The v6.3.0 notes stated schema 19 / API 3 in error; v6.3.0 shipped schema 22 / API 4.
- **Rust backend:** API 4 / schema 24. Native wheels built for schema 22 are rejected; use the wheel from this release.
- **NapCat is no longer bundled or downloaded**, because its pinned upstream download is gone. Install [NapCat](https://github.com/NapNeko/NapCatQQ) or another OneBot V11 implementation yourself. An existing NapCat installation is not removed.
- **Only OneBot V11 is installed.** The other 28 adapters (including OneBot V12, QQ official, Telegram, Discord, Feishu and DingTalk) are temporarily disabled because of a dependency advisory. Configured ones are skipped at boot with a warning. Restoration is tracked in [#134](https://github.com/Enoa-devteam/stella_project/issues/134).
- **stella CLI packages are no longer published.** Use the WebUI, or build `cli/` from source.
- **Online installers download WebView2** when the machine does not have it. Use an Offline installer on machines without internet access.
- **Proactive participation changed.** It is context-first, no longer gated by message count, and limited by `PROACTIVE_FREQUENCY` (default `1.0` per hour per conversation; `0` disables ordinary proactive participation and spontaneous sleep/wake announcements).
- **QQ and WebChat use the shared ingress bridge by default.** Set `STELLA_SHARED_INGRESS_ENABLED=false` and restart to restore the direct paths.
- **Background extraction may use more model budget**, because truncated memory extraction is now retried in smaller batches.

## What's Changed

### Features

- Split proactive participation (Aoede) and memory (Mneme) into separate subsystems, with `memory.*` compatibility aliases; added one-shot verification and persistent proactive frequency control (#129).
- Expanded the evidence contract that lets natural conversation become long-term memory, and added opt-in memory metadata and evidence-sufficiency guards, both off by default (#128).
- Added managed-runtime configuration revisions with apply and rollback, plus WebUI repairs (#123).
- Added versioned transport contracts, per-conversation policy, cross-platform message storage and bounded outbound delivery (#124), and payload-free delivery logging (#125).
- Capabilities can opt in to sending a tool's own output with `direct_reply = "tool_output"` (#133).

### Bug Fixes and Reliability

- Capability direct replies are no longer dropped, and tools with unfilled optional arguments are no longer called empty (#132, #133).
- MCP sessions survive protocol errors, renew after idle termination, and recover stale tool lists (#133).
- Group @ mentions are accepted anywhere in a message (#129).
- Memory extraction survives truncation and accepts English contractions (#137).
- Doctor no longer reports the managed Corona port as a conflict (#126).
- `deploy migrate --dry-run` and migration of a copy write only to the database being migrated (#140).
- Installers reference the llama.cpp asset of their own versioned Release instead of a disposable prerelease (#139).
- The llama.cpp web UI is pinned to the commit's release tag, and the Rust engine asset is published again (#138, #139).

### Build

- Faster release builds through pinned prebuilt tools and caches. Offline installers are stored uncompressed and are about 1.1 GB (#138).

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`. Do not copy only the main `.db` file of a running database while WAL is active.
2. Install with the OneClick installer or into a new program directory, preserving the existing data root.
3. When importing from another installation, preview first. After the real run, check that the report lists `memory/agent_memory.db` as imported:

   ```bash
   python -m deploy paths
   python -m deploy migrate --from <old-install> --dry-run
   python -m deploy migrate --from <old-install>
   ```

**Online installers of v6.0.1–v6.3.0 can no longer complete component installation**, because download URLs embedded in them are gone. Use v6.4.0.

The application version is 6.4.0. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.0-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.0-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.0-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.0-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.0-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.0-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.0-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default; the managed runtime is not ready for a default rollout.
- Not verified: clean-VM installation, GUI first boot, a complete online component installation, WebView2 installation on a machine without it, over-install upgrade from v6.3.0, real QQ/OneBot delivery and real-model acceptance.
- Proactive participation and memory quality are not accepted as product-ready; follow-ups are tracked in #136.
- Multiplatform adapters have no live-platform certification.
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

**升级前请先阅读不兼容变更。**

- **记忆库 schema 22 → 24**：首次启动自动迁移，并在数据库旁生成 `agent_memory.db.pre-v24-<时间戳>.bak`。v6.3.0 不会拒绝 v24 的库，回退时不要直接用旧版运行，须停止程序并恢复备份。v6.3.0 说明误写为 schema 19 / API 3，实际是 22 / 4。
- **Rust 后端为 API 4 / schema 24**：旧 wheel 会被拒绝，请使用本版本的 wheel。
- **不再内置或下载 NapCat**（上游下载源已失效）：请自行安装 NapCat 或其他 OneBot V11 实现；已安装的不会被删除。
- **只安装 OneBot V11 适配器**：其余 28 个（含 OneBot V12、QQ 官方、Telegram、Discord、飞书、钉钉）因依赖安全公告暂时停用，已配置的会在启动时跳过并告警（#134）。
- **不再发布 stella CLI 包**：请使用 WebUI，或从 `cli/` 源码构建。
- **Online 安装器在缺少 WebView2 时需联网下载**；离线机器请使用 Offline 安装器（约 1.1 GB）。
- **主动参与行为变化**：改为上下文优先、取消消息条数门槛，由 `PROACTIVE_FREQUENCY` 限频（默认每会话每小时 1.0 次；0 为关闭普通主动参与与自发睡眠/苏醒播报）。
- **QQ / WebChat 默认走共享入站**：`STELLA_SHARED_INGRESS_ENABLED=false` 并重启可恢复原路径。
- **后台记忆提取可能消耗更多模型额度**：截断时会拆分重试。
- **v6.0.1–v6.3.0 的 Online 安装器已无法完成组件安装**（内嵌下载地址失效），请使用 v6.4.0。

主要改进：Aoede / Mneme 子系统拆分、证据合同扩展、托管配置版本与回滚、会话策略与消息存储、能力直接回复与 MCP 会话修复；修复迁移预演写入目标库、安装器内嵌下载地址与 Rust 资产发布。

legacy 仍是默认入口。干净 VM、GUI 首启、完整在线组件安装、缺 WebView2 安装、从 v6.3.0 覆盖升级、真实 QQ 与真实模型均未验收。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.3.0...v6.4.0
