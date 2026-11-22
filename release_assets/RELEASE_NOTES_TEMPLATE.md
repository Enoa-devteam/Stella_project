# stella v6.4.1

This patch release builds on [v6.4.0](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0). When upgrading from v6.3.0 or earlier, read the [v6.4.0 breaking changes](https://github.com/Enoa-devteam/stella_project/releases/tag/v6.4.0) first: memory schema 22 → 24, no bundled NapCat, only the OneBot V11 adapter, and no CLI packages.

## What's Changed

### Bug Fixes

- **The desktop app now starts on Windows without the Visual C++ Redistributable.** v6.4.0, v6.3.0 and v6.2.0 fail there with "VCRUNTIME140_1.dll was not found". The C++ runtime is now linked statically.
- **The bundled llama.cpp backend now runs on such machines.** It ships the Visual C++ and OpenMP runtime DLLs beside `llama-server.exe`; previously it exited with `0xC0000135`.
- **Offline installers are smaller again.** v6.4.0 stored them uncompressed, which made them about 31% larger; they now use zlib.
- `docker-compose.yml` names the current image, `ghcr.io/enoa-devteam/stella_project`.

### Build

- The release build now rejects a desktop exe or backend package that needs a Visual C++ runtime it does not ship.

## Breaking Changes

- None since v6.4.0.

## Important: Smart App Control

The installers are **not code-signed**. On Windows 11 with **Smart App Control on**, Windows blocks them outright and offers no "Run anyway". On other systems SmartScreen shows an unknown-publisher warning. Check downloads against `SHA256SUMS.txt`.

## Upgrade and Compatibility

1. Stop stella and back up the complete `STELLA_HOME`.
2. Install over the existing installation or into a new program directory, preserving the existing data root.
3. The memory schema (24) and the Rust backend API (4) are unchanged since v6.4.0.

The application version is 6.4.1. The launcher, runtime-manager, native wheel, and private Dashboard keep independent component versions.

## Downloads

| Product | Asset |
| --- | --- |
| Online installer / Python | `Stella-OneClick-Python-v6.4.1-windows-amd64.exe` |
| Online installer / Rust | `Stella-OneClick-Rust-v6.4.1-windows-amd64.exe` |
| Offline installer / Python | `Stella-OneClick-Python-Offline-v6.4.1-windows-amd64.exe` |
| Offline installer / Rust | `Stella-OneClick-Rust-Offline-v6.4.1-windows-amd64.exe` |
| Standalone / Python | `Stella-Standalone-Python-v6.4.1-windows-amd64.zip` |
| Standalone / Rust | `Stella-Standalone-Rust-v6.4.1-windows-amd64.zip` |
| Rust engine package | `Stella-Rust_engine_version-v6.4.1-win64.zip` (attached shortly after publication) |

Additional assets include the CPU backend, WebUI, package catalog, release manifest, and `SHA256SUMS.txt`. Offline installers bundle the WebView2 runtime, Python, dependencies, components, the default embedding model, and the rendering kernel; online installers download what they need. A chat model must still be configured, and QQ still requires account login.

## Known Boundaries

- The legacy runtime remains the default.
- Not verified: WebView2 installation on a machine without it, real QQ/OneBot delivery, and real-model acceptance.
- Known issues: #142 (a failed table creation during migration is not reported) and #143 (no downgrade guard; restore the pre-migration backup to roll back).
- `VERSIONED_LAYOUT=0` remains the workflow default.

## 中文摘要

- **修复：没有 Visual C++ 运行库的 Windows 上桌面程序无法启动**（v6.4.0、v6.3.0、v6.2.0 均报「找不到 VCRUNTIME140_1.dll」），现已静态链接。
- **修复：随包 llama.cpp 后端在这类机器上以 `0xC0000135` 退出**，现随包携带 VC++ 与 OpenMP 运行库。
- **Offline 安装器恢复压缩**：v6.4.0 未压缩导致体积大了约 31%，现改用 zlib。
- `docker-compose.yml` 改用当前镜像名 `ghcr.io/enoa-devteam/stella_project`。
- **注意：安装器未经代码签名。开启「智能应用控制」的 Windows 11 会直接拦截，且没有「仍要运行」选项**；其他系统会显示 SmartScreen 未知发布者提示。
- 相对 v6.4.0 没有不兼容变更；从 v6.3.0 及更早版本升级时请先阅读 v6.4.0 的不兼容变更。

**Full Changelog**: https://github.com/Enoa-devteam/stella_project/compare/v6.4.0...v6.4.1
