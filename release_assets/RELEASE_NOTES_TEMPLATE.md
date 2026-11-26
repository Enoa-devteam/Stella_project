# stella v6.4.5

This maintenance release builds on [v6.4.4](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.4) and changes no features or data formats. When upgrading from v6.3.0 or earlier, read the [v6.4.0 breaking changes](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0) first: memory schema 22 → 24, no bundled NapCat, only the OneBot V11 adapter, and no CLI packages.

## What's Changed

### Improvements

- **Installer and desktop shell use the ureq 3 HTTP library** ([#210](https://github.com/Enoa-devteam/stella_project/issues/210)). This covers the first-start download of the embedded Python runtime, `get-pip` and wheels, the bot readiness check, and the model list in the setup page. Timeouts (120 s download, 10 s model list), resuming an interrupted runtime download, and the 401 / 403 / 404 messages for model endpoints are unchanged.
- **Rust memory engine:** SQLite binding rusqlite 0.43 (bundled SQLite updated with it), uuid 1.29 and pyo3 0.30. Building the native wheel from source now needs Rust 1.89 or newer ([#212](https://github.com/Enoa-devteam/stella_project/issues/212)). The Rust backend API (4) and memory schema (24) are unchanged.
- Dependency updates: TypeScript 6.0 for the private Dashboard, rustls 0.23.46, dompurify, tomli ≥ 2.5, and minor Rust updates within each crate's declared minimum Rust version.

## Breaking Changes

- None since v6.4.0.

## Important: Smart App Control

The installers are **not code-signed**. On Windows 11 with **Smart App Control on**, Windows blocks them outright and offers no "Run anyway". On other systems SmartScreen shows an unknown-publisher warning. Check downloads against `SHA256SUMS.txt`.

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`.
2. Install over the existing installation or into a new program directory, preserving the existing data root.
3. The memory schema (24) and the Rust backend API (4) are unchanged since v6.4.0.

The application version is 6.4.5. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.5-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.5-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.5-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.5-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.5-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.5-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.5-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel; online installers download what they need. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default.
- OneBot V12 is experimental and has not been tested against a real V12 implementation ([#186](https://github.com/Enoa-devteam/stella_project/issues/186)).
- The memory changes in v6.4.4 increase how many candidates are promoted, but the evaluation so far shows no measurable improvement in replies ([#136](https://github.com/Enoa-devteam/stella_project/issues/136) stays open).
- Online installers download from GitHub and Hugging Face and have no mirror ([#149](https://github.com/Enoa-devteam/stella_project/issues/149)). Where either is not reliably reachable, use an Offline installer.
- PRE_RELEASE_TEST_RESULT
- Not verified before publication: a complete Online installation (component URLs exist only after publication), the Offline and Rust installers in the Sandbox (CI install tests passed), Windows 10, real QQ / OneBot V11 delivery, OneBot V12 against a real implementation, and chat-model acceptance.
- An over-install from v6.3.0 or earlier leaves the old `memory/participation/` directory, which shadows the compatibility alias `memory.participation` for plugins that import it ([#146](https://github.com/Enoa-devteam/stella_project/issues/146)). stella itself imports `aoede.participation`. A clean program directory avoids this.
- Known issues: #142 (a failed table creation during migration is not reported) and #143 (no downgrade guard; restore the pre-migration backup to roll back).
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

- **维护版本，功能与数据格式不变。**
- 安装器与桌面壳的网络库升级到 ureq 3（#210），涉及首次启动下载 Python 运行时 / get-pip / 依赖、Bot 就绪探测、设置页读取模型列表。超时（下载 120 秒、模型列表 10 秒）、运行时下载断点续传，以及模型端点 401 / 403 / 404 的提示均不变。
- Rust 记忆引擎：rusqlite 0.43（随附 SQLite 一并更新）、uuid 1.29、pyo3 0.30；从源码构建 native wheel 需要 Rust 1.89 及以上（#212）。Rust 后端 API（4）与记忆 schema（24）不变。
- 依赖更新：私有 Dashboard 改用 TypeScript 6.0、rustls 0.23.46、dompurify、tomli ≥ 2.5 等。
- **注意：安装器未经代码签名。开启「智能应用控制」的 Windows 11 会直接拦截，且没有「仍要运行」选项**；其他系统会显示 SmartScreen 未知发布者提示。
- 相对 v6.4.0 没有不兼容变更；从 v6.3.0 及更早版本升级时请先阅读 v6.4.0 的不兼容变更。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.4.4...v6.4.5
