# stella v6.4.4

This patch release builds on [v6.4.3](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.3). When upgrading from v6.3.0 or earlier, read the [v6.4.0 breaking changes](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0) first: memory schema 22 → 24, no bundled NapCat, only the OneBot V11 adapter, and no CLI packages.

## What's Changed

### New Features

- **OneBot V12 (experimental).** stella can now receive and reply to private, group and channel messages over OneBot V12, the protocol intended for platforms other than QQ ([#134](https://github.com/Enoa-devteam/stella_project/issues/134)). Each V12 Bot must be declared in `STELLA_TRANSPORT_SETTINGS_JSON` with `adapter: "onebot-v12"`, `platform_scope` and `self_id`; undeclared Bots are ignored, and model replies and memory capture are off by default. Replies are text, and in groups and channels they quote the original message. Images and files, AstrBot plugins, commands, proactive speech and link heartbeat are still V11-only. V12 has not been tested against a real OneBot V12 implementation yet ([#186](https://github.com/Enoa-devteam/stella_project/issues/186)); keep using V11 for QQ. See the platform guide for setup.

### Bug Fixes

- **Replies to non-numeric user IDs were dropped.** The delivery scope check converted every transport user ID to a number, so replies to IDs such as `wxid_…` were silently discarded. QQ (numeric IDs) was not affected.
- **Long-term memory no longer accepts facts cut out of hypothetical, negated or quoted sentences** ([#136](https://github.com/Enoa-devteam/stella_project/issues/136)). Before, `如果我住在杭州就好了` ("if only I lived in Hangzhou") could be stored as `我住在杭州` ("I live in Hangzhou"). The check now looks at the whole sentence around the extracted fact. Memories accepted by earlier versions are not re-checked. Names with an apostrophe (`O'Brien`) are no longer discarded, and pronoun-only statements such as "I like it" are no longer stored.
- **Memory extraction is more compact.** The second extraction stage now returns only the exact quoted content, its source and its kind; the verification contract is derived by the server. On the local test model this reduced truncated extraction responses (29 of 41 → 7 of 23 in the same sample).
- **The runtime installer rejects ZIP entries that would be written outside the runtime folder.** An entry named like `C:/…` passed the old check and would have been written to that absolute path; only Windows permissions stopped it in testing. The archives stella downloads are checksum-verified, so this was not reachable with official downloads.
- **Cometa's Codex backend works again.** The pinned Codex SDK 0.159.2 is now rejected by the account backend for every real task (`model_not_found`). Cometa now uses openai-codex **0.171.0**, re-verified against the live App Server (completed, command and interrupted turns). Checking a turn after its event stream dropped also works again; before, it always reported "turn not found".

### Improvements

- Desktop and installer shells moved to Tauri 2.12 (tauri-build 2.7). The VC++ runtime is still linked statically, now through the supported setting.
- Rendering requires playwright 1.65.2 or newer (was 1.45). Existing installations upgrade the package on their next dependency install, which may download the rendering browser again (about 270 MB) when it is next needed.
- Dependency updates: pycryptodomex 3.24.2, vue-tsc 3, zip 9, sha2 0.11, rand 0.10, and minor updates.

## Breaking Changes

- None since v6.4.0. Adapters other than OneBot V11 and V12 were already unavailable since v6.4.0; their code is now explicitly short-circuited (`unsupportedInCore`).

## Important: Smart App Control

The installers are **not code-signed**. On Windows 11 with **Smart App Control on**, Windows blocks them outright and offers no "Run anyway". On other systems SmartScreen shows an unknown-publisher warning. Check downloads against `SHA256SUMS.txt`.

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`.
2. Install over the existing installation or into a new program directory, preserving the existing data root.
3. The memory schema (24) and the Rust backend API (4) are unchanged since v6.4.0.
4. Cometa users: reinstall the optional SDK with `pip install openai-codex==0.171.0 -i https://pypi.org/simple`.

The application version is 6.4.4. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.4-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.4-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.4-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.4-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.4-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.4-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.4-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel; online installers download what they need. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default.
- OneBot V12 is experimental and has not been tested against a real V12 implementation ([#186](https://github.com/Enoa-devteam/stella_project/issues/186)).
- The memory changes increase how many candidates are promoted, but the evaluation so far shows no measurable improvement in replies ([#136](https://github.com/Enoa-devteam/stella_project/issues/136) stays open).
- Online installers download from GitHub and Hugging Face and have no mirror ([#149](https://github.com/Enoa-devteam/stella_project/issues/149)). Where either is not reliably reachable, use an Offline installer.
- Tested before publication in a clean Windows 11 Sandbox (no VC++ runtime; Smart App Control off in the guest only), using the test build of this release: the **Python Offline installer with networking disabled** installed silently, the Tauri 2.12 shell opened the console setup page, components (`llama-cpu`, `qwen3-embedding-0.6b`) were installed from the bundled payload, and the bot reported version 6.4.4 with `core_phase: ready` about a minute after launch. The **Python Online installer** downloaded the runtime and dependencies with the loading view and live progress; its component download then ended with the expected HTTP 404 (this release's assets did not exist yet) and showed the error card with the original error. The Sandbox's WebView2 registration is broken on the test host, so `WEBVIEW2_BROWSER_EXECUTABLE_FOLDER` pointed at the on-disk runtime, as for v6.4.3.
- Not verified before publication: a complete Online installation (component URLs exist only after publication), the Rust installers in the Sandbox (CI install tests passed), Windows 10, real QQ / OneBot V11 delivery, OneBot V12 against a real implementation, chat-model acceptance, and Cometa tasks in the packaged app (the Codex SDK was verified separately against the live App Server).
- An over-install from v6.3.0 or earlier leaves the old `memory/participation/` directory, which shadows the compatibility alias `memory.participation` for plugins that import it ([#146](https://github.com/Enoa-devteam/stella_project/issues/146)). stella itself imports `aoede.participation`. A clean program directory avoids this.
- Known issues: #142 (a failed table creation during migration is not reported) and #143 (no downgrade guard; restore the pre-migration backup to roll back).
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

- **新增：OneBot V12（实验性）**（#134）。可经 OneBot V12 收发私聊、群聊与频道消息，面向 QQ 以外的平台。每个 V12 Bot 需在 `STELLA_TRANSPORT_SETTINGS_JSON` 中显式登记（`adapter: "onebot-v12"`、`platform_scope`、`self_id`），未登记的 Bot 会被忽略；模型回复与记忆采集默认关闭。图片 / 文件、AstrBot 插件、命令、主动发言、链路心跳仍只支持 V11。尚未对接真实 V12 实现验证（#186），QQ 请继续使用 V11。
- **修复：非数字用户 ID 的回复被丢弃**（如 `wxid_…`）；QQ 不受影响。
- **修复：长期记忆不再把假设句、否定句、引述句里截出的片段当作事实**（#136），例如「如果我住在杭州就好了」不再记成「我住在杭州」。旧版本已晋升的记忆不会回查。带撇号的名字不再被丢弃，「I like it」这类代词陈述不再入库；第二阶段提取改为紧凑格式，截断明显减少。
- **修复：运行时安装器拒绝会写到运行时目录之外的 ZIP 条目**（形如 `C:/…`）。官方下载有校验和，正常使用不受影响。
- **修复：Cometa 的 Codex 后端恢复可用。** 原固定的 SDK 0.159.2 已被账号后端拒绝（`model_not_found`），现改用 openai-codex **0.171.0** 并重新实测验证；断流后核对轮次状态也恢复正常。Cometa 用户请重新安装：`pip install openai-codex==0.171.0 -i https://pypi.org/simple`。
- 桌面壳与安装器升级到 Tauri 2.12，VC++ 运行库仍静态链接。渲染依赖要求 playwright ≥ 1.65.2，已安装的环境下次装依赖时会升级，需要渲染时可能重新下载浏览器内核（约 270MB）。
- **注意：安装器未经代码签名。开启「智能应用控制」的 Windows 11 会直接拦截，且没有「仍要运行」选项**；其他系统会显示 SmartScreen 未知发布者提示。
- 相对 v6.4.0 没有不兼容变更；从 v6.3.0 及更早版本升级时请先阅读 v6.4.0 的不兼容变更。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.4.3...v6.4.4
