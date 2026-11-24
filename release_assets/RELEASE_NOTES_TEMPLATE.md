# stella v6.4.3

This patch release builds on [v6.4.2](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.2). When upgrading from v6.3.0 or earlier, read the [v6.4.0 breaking changes](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0) first: memory schema 22 → 24, no bundled NapCat, only the OneBot V11 adapter, and no CLI packages.

## What's Changed

### Bug Fixes

- **The first start of an Online installer no longer says the backend is not running while it is still downloading.** Reading the configuration prepares the runtime, and on a first start that is the whole download of the runtime, dependencies and components. The window entered its loading view only afterwards, so for several minutes it showed "后端未运行" (backend not running) with a Retry button, and users reasonably concluded the installation had failed. The loading view, with live component progress and elapsed time, now appears before that step ([#145](https://github.com/Enoa-devteam/stella_project/issues/145)).

### Improvements

- The loading view shows the new animated stella logo, generated from the original 3D model.

## Breaking Changes

- None since v6.4.0.

## Important: Smart App Control

The installers are **not code-signed**. On Windows 11 with **Smart App Control on**, Windows blocks them outright and offers no "Run anyway". On other systems SmartScreen shows an unknown-publisher warning. Check downloads against `SHA256SUMS.txt`.

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`.
2. Install over the existing installation or into a new program directory, preserving the existing data root.
3. The memory schema (24) and the Rust backend API (4) are unchanged since v6.4.0.

The application version is 6.4.3. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.3-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.3-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.3-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.3-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.3-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.3-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.3-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel; online installers download what they need. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default.
- Online installers download from GitHub and Hugging Face and have no mirror ([#149](https://github.com/Enoa-devteam/stella_project/issues/149)). Where either is not reliably reachable, use an Offline installer.
- Tested before publication: pending (Windows 11 Sandbox check of the Online installer first start).
- An over-install from v6.3.0 or earlier leaves the old `memory/participation/` directory, which shadows the compatibility alias `memory.participation` for plugins that import it ([#146](https://github.com/Enoa-devteam/stella_project/issues/146)). stella itself imports `aoede.participation`. A clean program directory avoids this.
- Known issues: #142 (a failed table creation during migration is not reported) and #143 (no downgrade guard; restore the pre-migration backup to roll back).
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

- **修复：Online 安装器首次启动下载期间显示「后端未运行」**（#145）。读取配置会准备运行时，首次启动时这一步就是整段运行时、依赖与组件下载；过去窗口在这之后才进入加载视图，几分钟里一直显示「后端未运行」与重试按钮，用户会以为安装失败。现在这一步之前就显示加载视图，带组件实时进度与已用时。
- 加载视图使用新的 stella 动态 Logo（由原 3D 模型生成）。
- Online 安装器的组件来自 GitHub 与 Hugging Face，尚无镜像（#149）；无法稳定访问时请使用 Offline 安装器。
- **注意：安装器未经代码签名。开启「智能应用控制」的 Windows 11 会直接拦截，且没有「仍要运行」选项**；其他系统会显示 SmartScreen 未知发布者提示。
- 相对 v6.4.0 没有不兼容变更；从 v6.3.0 及更早版本升级时请先阅读 v6.4.0 的不兼容变更。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.4.2...v6.4.3
