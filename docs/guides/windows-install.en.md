# Windows Install, Upgrade, and Start

[中文](windows-install.md) | English · [Documentation](../README.en.md)

This page covers **Windows desktop** deployment. For Linux / remote servers, see the [Docker Deployment Guide](deployment-docker.en.md).

> **v2 control plane (current UI)**: point a browser at the bot's own port for the full management panel (auth / config / plugins / MCP / knowledge base / cron / live logs — see [WebUI management](webui.en.md)); the desktop shell (Tauri 2) embeds the same panel. The legacy native UI is retired, frozen at tag `gui-v1-final`.

## Current release notes (6.4.3)

- 6.4.3: while an Online installer's first start downloads the runtime and components, the window shows the loading view (animated logo, live progress and elapsed time) instead of "backend not running" with a Retry button ([#145](https://github.com/Enoa-devteam/stella_project/issues/145)).
- Since 6.4.2: fixes Online installers failing to download components on a clean Windows installation with `CERTIFICATE_VERIFY_FAILED` (v6.0.1–v6.4.1 are affected); an interrupted download now resumes.
- Since 6.4.1: the desktop app and the bundled llama.cpp backend start on Windows without the Visual C++ runtime, and the first start of a new installation no longer fails.
- Online installers download components from GitHub and Hugging Face, with no mirror yet; where they are not reliably reachable, use an Offline installer (about 1.2 GB).
- Installers are not code-signed: Windows 11 with Smart App Control on blocks them.
- Since 6.4.0: memory schema 24 (rollback requires restoring the pre-migration backup), no bundled NapCat, no CLI packages, and only the OneBot V11 adapter for now.

Back up the complete data root before upgrading; when importing from an old directory, first run `python -m deploy migrate --from <old-install> --dry-run`. See the [release notes](../../release_assets/RELEASE_NOTES_TEMPLATE.md).

## Requirements

| Component | Requirement |
|---|---|
| OS | Windows 10/11 x64 (without WebView2: OneClick Offline bundles an offline installer, OneClick Online downloads it; Standalone relies on the system-provided runtime) |
| Python | 3.10+ (OneClick installers bundle the embedded Python; Standalone archives require your own installation) |
| Framework | [NoneBot 2](https://nonebot.dev/) |
| QQ protocol endpoint | [NapCat](https://github.com/NapNeko/NapCatQQ) or another OneBot V11 implementation (install it and log in by QR code yourself; installers no longer bundle NapCat since 2026-11) |
| Model service | Optional local [LM Studio](https://lmstudio.ai/) / `llama.cpp` Runtime, or any OpenAI-compatible online API (provide the address + API key); the two can be mixed, and AI can be disabled |

## 📦 Download & Install

- Step 1: Choose a Windows product from [Releases](https://github.com/Eternal-Wanderer-Vegetable/stella_project/releases). They come in two product lines, split by "does it set up the runtime for you":

  - **OneClick installer (recommended)**: `Stella-OneClick-Python-vX.Y.Z-windows-amd64.exe`, a single-file installer — double-click to install. On first launch it automatically prepares the embedded Python, the `llama.cpp` CPU backend, and the `qwen3-embedding-0.6b` embedding model. **Since 2026-11 the installers no longer bundle NapCat** (its upstream download source is gone); install a QQ protocol endpoint yourself (see "Connecting QQ" below). To use the Rust memory engine, download `Stella-OneClick-Rust-vX.Y.Z-windows-amd64.exe` instead; the engine is prepared during installation.
  - **OneClick installer (offline)**: `Stella-OneClick-Python-Offline-vX.Y.Z-windows-amd64.exe` (Rust variant: `Stella-OneClick-Rust-Offline-*`). The installation flow is identical to the online installer, but the embedded Python, all Python dependencies, the `llama.cpp` CPU backend, NapCat, the embedding model, and the browser rendering kernel **are all bundled — installation and rendering require no network access at all** — ideal for restricted or offline networks. The trade-off is a download size of roughly 1 GB.
  - **Standalone archive**: `Stella-Standalone-Python-vX.Y.Z-windows-amd64.zip`, extract and run. It contains **only stella itself** — you provide Python 3.10+ and NapCat yourself, and it does not auto-download `llama.cpp` or any model. The Rust variant (`Stella-Standalone-Rust-*.zip`) additionally bundles the Rust memory-engine wheel, which is installed offline automatically on first launch.

  Both product lines offer a `Stella.exe` graphical interface (recommended) and a `start.bat` command-line flow. `Stella.exe` runs an environment check on launch: if not configured, it opens the Configuration page; if there are blocking issues, it opens the Environment Check page; if everything is normal, it goes directly to the Run Status page. `start.bat` opens the command-line configuration wizard and starts the Bot. **Do not install both product lines into the same directory.**

> **About the "Unknown publisher" prompt**: current Windows installers are not code-signed yet (enforced signing will return once the certificate is in place), so SmartScreen may show an "Unknown publisher" warning — this is expected. Every release ships a `SHA256SUMS.txt` so you can verify your download; the release page notes and the release workflow are the only sources of truth.

> AI can be disabled. When AI is disabled or a local model is unavailable, the basic Bot, OneBot diagnostics, and deployment management remain available.

- Step 2: Prepare the remaining components for your setup:

  - Connecting QQ: for both OneClick and Standalone, first install and log in to [NapCat](https://github.com/NapNeko/NapCatQQ) or another OneBot V11 implementation yourself (login requires scanning the QR code), then add a "WebSocket client" under Network in the NapCat WebUI pointing at the Bot (reverse WS, address `ws://127.0.0.1:8080/onebot/v11/ws`).
  - If you use a local chat model: install [LM Studio](https://lmstudio.ai/) and load a model (OneClick already bundles the `llama.cpp` CPU backend and the embedding model). LM Studio is not required for online-only setups.

> **Tip**: The first run downloads and executes Python. Your computer's security software may report this as suspicious activity and block it; add it to the trusted list if necessary.

- Step 3:
  - 1. After opening `Stella.exe` for the first time, the configuration UI appears. First fill in the **listening port** (the reverse WS port configured in NapCat in Step 2) and the **group number** that stella should join.
  - 2. Scroll down to the Model Services section, choose a **one-click preset** according to your deployment mode, and fill in the corresponding endpoint cards:
    - **All local** -> Click `纯本地`, then fill in the address and model ID for an OpenAI-compatible local endpoint such as LM Studio or llama.cpp. The Test Connection button reads back the service's model list.
    - **All online / Hybrid** -> Click `纯在线（双 key）` or `混合（对话在线 · 整合本地）`, then fill in the provider address, API key, and model ID once in each of the two online cards. **The two keys must be different**; see [Three Deployment Modes](../reference/configuration.en.md#three-deployment-modes) for why.
  - 3. After configuration is complete, click "Save and Check". The program automatically switches to the Run Status page. Click "Start".

> Have a problem? Join the developer's QQ group: 263402786, and @ the (currently sole) developer Eternal-Wanderer-Vegetable in the group.

## Configuration

It is recommended to make changes through the built-in Advanced Options form in `Stella.exe`. **Manually editing .env is not recommended.**

See the **[Configuration Reference](../reference/configuration.en.md)** for all configuration options and their descriptions.

## Starting

Click "Start" on the Run Status page in `Stella.exe` (it first runs the doctor check), or double-click `start.bat` to use the command-line flow. @ the Bot in a group to start a conversation.

To start a development instance from source, see [Environment setup](../development/environment.en.md#starting-a-development-instance). For plugins, see [Installing plugins](plugins.en.md). When something goes wrong, start with [Troubleshooting](../development/troubleshooting.en.md).

## ⬆️ Upgrading from an older version

1. Run `stop.bat` to stop the program.
2. OneClick: run the new version's installer directly. Standalone: extract the new version into a new directory.
3. Double-click `Stella.exe` (or `start.bat`) -> confirm "Import Configuration".

Configuration, memories, personality, space settings, and installed plugins are moved automatically; the database is upgraded automatically, and `runtime/` is reused automatically (saving one approximately 100 MB download). The old directory is **read-only throughout**. Regardless of success or failure, the old installation remains runnable in place, so you can safely retry. The import report is written to the current `STELLA_HOME/migration_report.md`. Command-line equivalents:

```bash
python -m deploy migrate --dry-run   # Preview first (runs once on a database copy)
python -m deploy migrate             # Execute
```

OneClick installs additionally support **atomic versioned upgrades**: `python -m deploy upgrade <extracted-new-version-dir> --version X.Y.Z` verifies and then flips the activation record; if anything goes wrong, `python -m deploy upgrade --rollback` flips back to the retained previous version tree (works both ways).

The versioned upgrade tool and default installer layout are separate: release CI uses `VERSIONED_LAYOUT=0`, leaving launcher relocation disabled. See [Source contracts](../development/contracts.en.md) for conditions.

Upgrading from 2.x also does not require losing memories: the old database is migrated automatically (columns are renamed, records are reassigned by shared space, and each user profile is placed in the space containing the most of that user's messages).

## Where user data lives

It depends on the product line and installation history (`python -m deploy paths` shows the actual location and which rule matched):

- **Fresh OneClick installs**: the data root defaults to a location **outside the program directory**, `%LOCALAPPDATA%\stella\Data`, recorded in the machine-level pointer file `%LOCALAPPDATA%\stella\home.txt` — reinstalling, uninstalling, or upgrading never touches the data. An existing data root (old sibling directory, portable directory, or pointer target) is always reused, **never migrated**.
- **Standalone and manual deployments**: data defaults to `StellaData/`, **at the same level as** the program directory:

```text
D:\your-directory\
  stella\                <- Program directory (replace the whole directory when upgrading; safe
                            to delete. Standalone archives have no inner folder — the extract
                            target *is* this directory)
  StellaData\            <- Your data (untouched during upgrades)
```

- **Portable mode (both product lines)**: to make the program and data self-contained (for copying the whole setup to a USB drive), manually create a `StellaData\` subdirectory in the program directory. The program will prefer it, but the cost is that it will be replaced or deleted along with the program directory; import or back up your data before upgrading.

After that, upgrading only requires replacing the program directory; the data does not need to be touched. Cleaning up old version folders will not affect the data. For the full data-root resolution rules, see [Configuration Reference](../reference/configuration.en.md#two-root-directories-program-and-data).
