# stella v6.4.2

This patch release builds on [v6.4.1](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.1). When upgrading from v6.3.0 or earlier, read the [v6.4.0 breaking changes](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0) first: memory schema 22 → 24, no bundled NapCat, only the OneBot V11 adapter, and no CLI packages.

## What's Changed

### Bug Fixes

- **Online installers can download components on a clean Windows installation.** v6.0.1–v6.4.1 checked HTTPS certificates only against the root certificates already on the machine. A new Windows installation fetches most of them when first needed, so downloads from GitHub and Hugging Face failed with `CERTIFICATE_VERIFY_FAILED`. Downloads now use the Windows certificate verifier (through `truststore`), which fetches missing roots and accepts company root certificates.
- **An interrupted download resumes.** A connection that stalled or dropped while a file was downloading ended the installation, or discarded what had already arrived. It is now retried from where it stopped.
- **The newest llama.cpp backend is chosen by version number.** Versions were compared as text, so 6.4.10 would have lost to 6.4.9 ([#147](https://github.com/Enoa-devteam/stella_project/issues/147)).

## Breaking Changes

- None since v6.4.0.

## Important: Smart App Control

The installers are **not code-signed**. On Windows 11 with **Smart App Control on**, Windows blocks them outright and offers no "Run anyway". On other systems SmartScreen shows an unknown-publisher warning. Check downloads against `SHA256SUMS.txt`.

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`.
2. Install over the existing installation or into a new program directory, preserving the existing data root.
3. The memory schema (24) and the Rust backend API (4) are unchanged since v6.4.0.

The application version is 6.4.2. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.2-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.2-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.2-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.2-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.2-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.2-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.2-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel; online installers download what they need. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default.
- Online installers download from GitHub and Hugging Face and have no mirror ([#149](https://github.com/Enoa-devteam/stella_project/issues/149)). Where either is not reliably reachable, use an Offline installer.
- Tested before publication in a clean Windows 11 Sandbox (no VC++ runtime, Smart App Control off): the Python Offline installer opens the setup panel without network access. The Online installers install the runtime and dependencies; from that installed runtime, the downloader verified a real release asset on a machine whose root certificates had not been fetched yet, which failed with `CERTIFICATE_VERIFY_FAILED` before this release.
- Not verified: a complete Online installation of this version (its download URL exists only after publication, and direct access to GitHub from the test network was intermittent), Standalone `start.bat`, WebView2 installation on a machine without it, Windows 10, real QQ/OneBot delivery, and chat-model acceptance.
- During the first start of an Online installer, the window says the backend is not running while the runtime and components are still downloading ([#145](https://github.com/Enoa-devteam/stella_project/issues/145)). Wait for it to finish; this can take several minutes.
- An over-install from v6.3.0 or earlier leaves the old `memory/participation/` directory, which shadows the compatibility alias `memory.participation` for plugins that import it ([#146](https://github.com/Enoa-devteam/stella_project/issues/146)). stella itself imports `aoede.participation`. A clean program directory avoids this.
- Known issues: #142 (a failed table creation during migration is not reported) and #143 (no downgrade guard; restore the pre-migration backup to roll back).
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

- **修复：Online 安装器在干净的 Windows 上无法下载组件**（v6.0.1–v6.4.1：只按本机已有的根证书校验 HTTPS，而新装的 Windows 多数根证书要用到时才下载，于是报 `CERTIFICATE_VERIFY_FAILED`）。现改用 Windows 证书验证（`truststore`），会自动获取缺失的根证书，也接受企业根证书。
- **修复：下载中途断线或卡住会直接失败或丢弃已下载部分**，现从中断处续传重试。
- **修复：按版本号而非字符串选择最新的 llama.cpp 后端**（否则 6.4.10 会输给 6.4.9，#147）。
- Online 安装器的组件来自 GitHub 与 Hugging Face，尚无镜像（#149）；无法稳定访问时请使用 Offline 安装器。
- **注意：安装器未经代码签名。开启「智能应用控制」的 Windows 11 会直接拦截，且没有「仍要运行」选项**；其他系统会显示 SmartScreen 未知发布者提示。
- 相对 v6.4.0 没有不兼容变更；从 v6.3.0 及更早版本升级时请先阅读 v6.4.0 的不兼容变更。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.4.1...v6.4.2
