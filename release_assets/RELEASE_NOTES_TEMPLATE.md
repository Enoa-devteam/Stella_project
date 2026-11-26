# stella v6.4.6

This maintenance release builds on [v6.4.5](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.5) and changes no features or data formats. When upgrading from v6.3.0 or earlier, read the [v6.4.0 breaking changes](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0) first: memory schema 22 → 24, no bundled NapCat, only the OneBot V11 adapter, and no CLI packages.

## What's Changed

### Improvements

- **The management panel (WebUI and desktop shell) now uses Vuetify 4** ([#211](https://github.com/Enoa-devteam/stella_project/issues/211)). Pages keep the previous layout and spacing; text sizes follow the Material Design 3 scale (12–24 px sizes unchanged), shadows are slightly softer, and button labels are no longer forced to upper case. Between 840 and 959 px window width, some two-column card groups now sit side by side instead of stacked. The sidebar still collapses to the icon rail below 1280 px.

## Breaking Changes

- None since v6.4.0.

## Important: Smart App Control

The installers are **not code-signed**. On Windows 11 with **Smart App Control on**, Windows blocks them outright and offers no "Run anyway". On other systems SmartScreen shows an unknown-publisher warning. Check downloads against `SHA256SUMS.txt`.

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`.
2. Install over the existing installation or into a new program directory, preserving the existing data root.
3. The memory schema (24) and the Rust backend API (4) are unchanged since v6.4.0.

The application version is 6.4.6. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.6-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.6-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.6-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.6-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.6-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.6-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.6-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel; online installers download what they need. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default.
- OneBot V12 is experimental and has not been tested against a real V12 implementation ([#186](https://github.com/Enoa-devteam/stella_project/issues/186)).
- The memory changes in v6.4.4 increase how many candidates are promoted, but the evaluation so far shows no measurable improvement in replies ([#136](https://github.com/Enoa-devteam/stella_project/issues/136) stays open).
- Online installers download from GitHub and Hugging Face and have no mirror ([#149](https://github.com/Enoa-devteam/stella_project/issues/149)). Where either is not reliably reachable, use an Offline installer.
- PRETEST_PLACEHOLDER
- An over-install from v6.3.0 or earlier leaves the old `memory/participation/` directory, which shadows the compatibility alias `memory.participation` for plugins that import it ([#146](https://github.com/Enoa-devteam/stella_project/issues/146)). stella itself imports `aoede.participation`. A clean program directory avoids this.
- Known issues: #142 (a failed table creation during migration is not reported) and #143 (no downgrade guard; restore the pre-migration backup to roll back).
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

- **维护版本，功能与数据格式不变。**
- 管理面板（WebUI 与桌面壳）升级到 Vuetify 4（#211）。页面版式与间距保持不变；字号按 Material Design 3 档位（12–24 px 档不变），阴影略淡，按钮文字不再强制大写。窗口宽 840–959 px 时，部分双列卡片由上下排列改为并排。侧栏仍在 1280 px 以下收成图标栏。
- **注意：安装器未经代码签名。开启「智能应用控制」的 Windows 11 会直接拦截，且没有「仍要运行」选项**；其他系统会显示 SmartScreen 未知发布者提示。
- 相对 v6.4.0 没有不兼容变更；从 v6.3.0 及更早版本升级时请先阅读 v6.4.0 的不兼容变更。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.4.5...v6.4.6
