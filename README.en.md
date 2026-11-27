<div align="center">

![Title Image](assets/pic/Title_Image(Second_Edition)_Compressed_version.jpg)

# 🌟 Stella

**A cross-platform, human-like group-chat bot built on OneBot V11/V12**

*-- Designed natively for small-context, locally deployed models, and compatible with online APIs*

[![CI](https://github.com/Enoa-devteam/stella_project/actions/workflows/ci.yml/badge.svg)](https://github.com/Enoa-devteam/stella_project/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Enoa-devteam/stella_project)](https://github.com/Enoa-devteam/stella_project/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![NoneBot2](https://img.shields.io/badge/NoneBot-2-ea5252)](https://nonebot.dev/)
[![OneBot](https://img.shields.io/badge/OneBot-V11%20%2F%20V12-black)](https://onebot.dev/)
[![Rust](https://img.shields.io/badge/Rust-1.89%2B-dea584?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docs/guides/deployment-docker.en.md)

[中文](README.md) | English

</div>

---

Stella is designed natively for large language models that can be deployed on consumer hardware. It needs a model context window of only **8192 tokens** to run.

You decide where the models come from:
- **All local**: chat on the GPU and memory consolidation on the CPU are scheduled separately, so they do not compete for resources, and no chat data leaves your machine.
- **All online**: provide any OpenAI-compatible API and run without a local graphics card.
- **Hybrid**: hand difficult conversational reasoning to an online model, and keep frequent tasks such as memory consolidation and session compression local.

> In all-local mode, routing decisions, summary compression, and plugin card rendering all happen locally. Only networked plugins (such as weather or anime lookups) send external requests while they run.

> **OneBot V12 is an experimental feature.** V12 support is available by default and is meant for platforms other than QQ, but it has not yet been verified end to end against a real protocol implementation ([#186](https://github.com/Enoa-devteam/stella_project/issues/186)), and it covers less than V11. Use OneBot V11 for QQ and in production. See [Platform adapters · OneBot V12](docs/guides/platforms.en.md#onebot-v12).

## ✨ Features

### 🪶 Runs in a small window

- **🧰 Tools are decoupled from personality** -- Capability routing first decides which tool a message needs. Tools run outside the chat context and hand back a single conclusion to Stella, so installing more plugins never eats into the conversation window. → [Capability system](docs/architecture/capability-system.en.md)
- **🗜 Long conversations stay connected** -- Early conversation that rolls out of the window is compressed into a recap automatically. The session summary, recent raw messages, and topic summary never overlap, and each has its own adjustable budget. → [Budget split](docs/reference/configuration.en.md#budget-split-of-the-8192-working-window)
- **🎯 Memories are injected on demand** -- Only a few filtered memories relevant to the current conversation are injected. Boundaries, dietary restrictions, and similar information only constrain behavior and are never brought up as topics. → [Memory system](docs/architecture/memory-system.en.md)

### 🧠 Remembers, and forgets

- **🔍 Memories need evidence** -- Candidates come in easily, but promotion is strict: confidence accumulates only when the same thing is mentioned repeatedly, something a user tells the Bot directly can be accepted after one mention, and candidates without new evidence for a long time are discarded. Filtering happens in an auditable, reversible database and does not use the conversation budget.
- **🔎 Hybrid search** -- SQLite FTS5 full-text indexing with multidimensional weighted ranking, plus optional local embedding semantic search that falls back automatically when the service is unavailable.
- **♻️ It forgets** -- Lifetimes are set per memory type, low-value memories are archived automatically, and long memories are split into atomic facts.
- **📚 Standalone knowledge base** -- A document library kept separate from personal memories. It imports Markdown / TXT / PDF / DOCX / URLs and has a review-and-publish workflow and citation-style injection. → [Knowledge base](docs/architecture/knowledge-base.en.md)

### 💬 Gets along like a group member

- **🙋 Starts conversations** -- Information picked up passively in group chats is sparse, so Stella @-mentions active members to chat or confirm memories, within daily quotas, per-user cooldowns, and back-off after repeated non-responses.
- **🏠 Shared spaces across groups** -- Several groups can belong to one space and share user profiles, long-term memories, and personality, while message history, topic state, and mute switches stay isolated per group.
- **🎭 Expression evolves with the group** (off by default) -- Learns from reply outcomes which phrasings are worth reusing and what the group's slang means, starting in a shadow mode that only records and never intervenes. → [Configuration reference](docs/reference/configuration.en.md)
- **🖼 It can see images** (off by default) -- Once a vision model endpoint is bound, images in @-mentioned messages are captioned into text before entering the conversation. Without a binding, behavior is unchanged.
- **⏰ Scheduled tasks** (off by default) -- Group members can schedule cron reminders, and admins can set up bounded scheduled Agent tasks. → [Scheduling](docs/guides/scheduling.en.md)

### 🛠 Deployment and operations

- **🔄 Seven model roles, mixed freely** -- Conversation, capability routing, plugin borrowing, session compression, memory consolidation, memory extraction, and image captioning each choose their own endpoint, combining local and online freely. Changing models or deployment modes does not require rebuilding the memory database. → [Endpoints and roles](docs/reference/configuration.en.md#endpoint-and-role-two-layer-configuration)
- **💰 Usage and budget are visible** -- Online token usage is logged daily by role, endpoint, and model, and you can see the provider's prefix-cache hit rate. When the daily budget is exceeded, only memory consolidation pauses by default; the group chat continues as usual. → [LLM budget](docs/architecture/llm-budget.en.md)
- **🖥 WebUI and desktop app** -- The browser and the Windows desktop app share one admin panel, covering configuration, environment checks, runtime status, and management of the knowledge base, Skills, scheduled tasks, and more. → [WebUI](docs/guides/webui.en.md)

### 🔌 Platforms and ecosystem

- **🔗 OneBot V11 / V12** -- QQ connects through a OneBot V11 implementation (such as NapCat). OneBot V12 targets other platforms and is currently **experimental** (see the note above). → [Platform adapters](docs/guides/platforms.en.md)
- **🧩 AstrBot plugin compatibility** -- Drop existing AstrBot plugins into `data/plugins/` and they run without source changes. Plugin cards are rendered by local Chromium. → [Installing plugins](docs/guides/plugins.en.md)
- **🤖 Skills and external Agents** -- Supports Anthropic-style Skills whose scripts run in a controlled sandbox, and can delegate long tasks such as coding and research to OpenAI Codex (Cometa). → [Skills](docs/guides/skills.en.md) · [Cometa](docs/guides/cometa.en.md)
- **🧪 Extensible and verifiable** -- Pipeline pre/post Hooks and automatic loading from the extensions directory. Unit, integration, and vendor-neutral contract tests cover memory promotion, cross-user isolation, and routing fallback, with probe regressions against real models. → [Development guide](docs/development/README.en.md)

## 🚀 Installation

Stella needs two things: a OneBot protocol implementation ([NapCat](https://github.com/NapNeko/NapCatQQ) is recommended for QQ) and at least one model service (local [LM Studio](https://lmstudio.ai/) / `llama.cpp`, or any OpenAI-compatible API).

### Windows (recommended)

Download one of these from [Releases](https://github.com/Enoa-devteam/stella_project/releases):

| Package | Best for |
|---|---|
| `Stella-OneClick-Python-vX.Y.Z-windows-amd64.exe` | Most users. On first launch it prepares Python, the `llama.cpp` CPU backend, and the embedding model (needs access to GitHub and Hugging Face) |
| `Stella-OneClick-Python-Offline-vX.Y.Z-windows-amd64.exe` | Restricted networks or intranets. The runtime and models are bundled, about 1.2 GB |
| `Stella-Standalone-Python-vX.Y.Z-windows-amd64.zip` | You already have Python 3.10+ and only need Stella itself |

For the Rust memory engine, download the matching package with `Rust` instead of `Python` in its name.

1. Install NapCat and log in by scanning the QR code. In its WebUI, under Network Configuration, add a WebSocket Client with the address `ws://127.0.0.1:8080/onebot/v11/ws`.
2. Open `Stella.exe` and fill in the listening port and group numbers. Under Model Services, choose a one-click preset (all local / all online / hybrid) and complete the endpoint address, API key, and model ID.
3. Click Save and Check, then click Start on the Runtime Status page.

> The installers are not code-signed yet: SmartScreen may warn about an unknown publisher, and you can verify files with the `SHA256SUMS.txt` attached to each Release. Windows 11 with Smart App Control enabled blocks them outright.

For the full steps, upgrades, and data locations, see [Windows install, upgrade, and start](docs/guides/windows-install.en.md).

### Docker (Linux server)

```bash
git clone https://github.com/Enoa-devteam/stella_project.git
cd stella_project
# First pin the NapCat image digest in .env and prepare a writable StellaData directory, as described in the guide
docker compose build
docker compose run --rm stella python -m deploy init   # use 0.0.0.0 as the listen address
docker compose up -d
```

For NapCat login, network configuration, and migrating from Windows, see the [Docker deployment guide](docs/guides/deployment-docker.en.md).

### From source

```bash
pip install -r requirements.txt
python -m deploy init    # generate the configuration
python -m deploy doctor  # environment self-check
python -m deploy start   # starts the Corona control plane and the managed bot process
```

Intended for development and debugging. See [Starting a development instance](docs/development/environment.en.md#starting-a-development-instance).

## 📖 Documentation

Use the [documentation index](docs/README.en.md) for guides, architecture, reference, development and archives. Coding agents start at [AGENTS.md](AGENTS.md). Current branch compatibility is in [Source contracts](docs/development/contracts.en.md).

| Document | Contents |
|---|---|
| [Windows install, upgrade, and start](docs/guides/windows-install.en.md) | Download and install, first configuration, upgrade, data location (start here) |
| [Installing plugins](docs/guides/plugins.en.md) | Install AstrBot plugins, add capability declarations, confirm routing |
| [Architecture](docs/architecture/README.en.md) | Directory structure, message-processing flow, module responsibilities, and the AstrBot compatibility layer |
| [Memory System](docs/architecture/memory-system.en.md) | Rationale for two-layer filtering, promotion rules, and search strategy |
| [Capability System](docs/architecture/capability-system.en.md) | Capability Router and Comes: how tools execute outside the chat context |
| [Plugin Integration Specification](docs/reference/plugin-spec.en.md) | Writing a plugin Stella can use in full: declaration format, the two paths, the failure contract, the self-check tool |
| [Configuration Reference](docs/reference/configuration.en.md) | Two-layer endpoint x role model configuration, all configuration options, and tuning recommendations |
| [Docker Deployment Guide](docs/guides/deployment-docker.en.md) | Containerized deployment on a remote server: build or pull the image, configure, migrate from Windows, upgrade and back up |
| [Development Guide](docs/development/README.en.md) | Tests, probe scripts, CI, and contribution workflow |

> Design process records (specification drafts, checkpoints, defect reports, and test checklists) are in [`design_docs/`](design_docs).

## 📄 License

This project is released under the **[GNU Affero General Public License v3.0](LICENSE)** (AGPL v3.0) and comes with **additional terms that don’t conflict with the main license**. See the LICENSE file and the copyright notices at the top of each source file for details.

## 💛 Acknowledgements

This project received encouragement and support from many people and organizations during development:

- My parents provided the most important financial support. Without them, none of this could have begun.
- The inspiration came from discussions with [@t1mb2rg](https://github.com/t1mb2rg) and arguments with [@CST-Cat](https://github.com/CST-Cat). Thank you for contributing your own ideas.
- The [Lumi_Nox](https://github.com/MIO-456/Lumi_Nox) project developed by [@MIO-456](https://github.com/MIO-456) inspired the development of this project.
- Thanks to [@vowm3440](https://github.com/vowm3440), [@CST-Cat](https://github.com/CST-Cat), and [@higashitaniyume](https://github.com/higashitaniyume) for helping me find public resources that support this project. Without their generous sharing, this project wouldn't have been possible.
- Thanks to [@qian-o](https://github.com/qian-o) and their companions, as well as [@MIO-456](https://github.com/MIO-456) and their companions. Without their encouragement, there would have been no motivation to start developing this project.
- Thanks to [@vowm3440](https://github.com/vowm3440) for continuous deployment and testing in QQ groups. Many directions for improvement have emerged precisely from observing examples of this deployment.
- Thanks to the Bilibili video creator [Ruuuuusty](https://space.bilibili.com/650991829) for turning my and chat-GPT's ideas about the Stella logo into reality.
- This project received support from the following organizations during development:
  - **Model providers**: Deepseek, OpenAI (ChatGPT), Google (Gemini, Gemma), Tongyi Qianwen (text-embedding-qwen3-embedding-0.6b), and ~~Anthropic~~. This project could not have been created without their excellent models as a foundation.
  - **Coding Agent**: [Opencode](https://github.com/anomalyco/opencode), thank you to Opencode for its tremendous support of this project.
  - **Open-source repositories**: [nonebot2](https://github.com/nonebot/nonebot2), [NapCatQQ](https://github.com/NapNeko/NapCatQQ), and all third-party libraries referenced in the source code. Salute to all developers and maintainers involved. This project also aims to follow in the footsteps of [AstrBot](https://github.com/AstrBotDevs/AstrBot) and [MaiBot](https://github.com/Mai-with-u/MaiBot), creating a genuine AI friend that can complete the entire loop locally without handing over group-chat information and personal privacy.
  - **Developer community**: [Linux Do](https://linux.do)
- Special thanks to Freya; this work is dedicated to you. My journey of exploration began with your gift, and it is time to offer an imperfect return gift.
