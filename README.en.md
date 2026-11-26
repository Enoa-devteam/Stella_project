<div align="center">

![Title Image](assets/pic/Title_Image(Second_Edition)_Compressed_version.jpg)


# 🌟 Stella

**A QQ group-chat bot for human-like conversation powered by a memory system**

*-- Designed for an 8K context window, with support for both local small models and online APIs*

[![CI](https://github.com/Eternal-Wanderer-Vegetable/Stella_project/actions/workflows/ci.yml/badge.svg)](https://github.com/Eternal-Wanderer-Vegetable/Stella_project/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![NoneBot2](https://img.shields.io/badge/NoneBot-2-ea5252)](https://nonebot.dev/)
[![OneBot V11](https://img.shields.io/badge/OneBot-V11-black)](https://onebot.dev/)
[![Rust](https://img.shields.io/badge/Rust-1.89%2B-dea584?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Tauri](https://img.shields.io/badge/Tauri-2-24C8DB?logo=tauri&logoColor=white)](https://tauri.app/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docs/deployment-docker.en.md)

[中文](README.md) | English

</div>

---


Stella does more than send messages to a large model and return a reply. It turns scattered information from group chats into **searchable, verifiable, and forgetful memories**, and proactively speaks up to learn about you at the right time.

Stella is designed around a small context window: the baseline limit is **8192 tokens**. Personality, memories, conversation history, and tool results all have to coexist within that small budget, so simply piling on prompts is not viable. The budget is therefore divided: memories are filtered in the database before being injected, tools run outside the chat context and return only a single conclusion, and conversations that roll out of the window are automatically compressed into a recap. **No matter how many plugins you install, they do not consume the conversation window.** A small window works, and a larger one naturally gives you more room; the reverse is not true: an architecture that assumes an unlimited window will fall apart on 8K.

You decide where the models come from.
- **All local**: the chat model runs on your GPU and a small model handles memory consolidation on your CPU. They do not compete for resources, and no group-chat content leaves your machine.
- **All online**: provide an OpenAI-compatible API and run without a graphics card.
- **Hybrid**: delegate conversation generation to an online model, keep frequent, low-difficulty work such as memory consolidation and session compression local, and send only the step requiring strong reasoning online.

> Note: With the all-local deployment mode, the data truly stays off the network. Networked tools (such as weather and anime lookups) send requests and return actual data themselves, while deciding whether to use a tool, compressing its result into a summary, and rendering plugin cards as images all happen locally.

## ✨ Features

### Works within an **8192-token** context budget

- **🧰 Capabilities are decoupled from personality** -- The Router first determines what capability a message needs. Tools execute **outside the chat context** and return only one compressed conclusion to Stella. Tool descriptions and raw results never enter the personality prompt, so installing more plugins cannot crowd out the conversation window.

- **🗜 Long conversations stay connected** -- Earlier conversations that roll out of the context window are automatically compressed into a recap. The three context layers (session summary / raw tail / topic summary) are divided by message ID and never overlap, with independently adjustable budgets.

- **🎯 Memories are injected by partition** -- Chat material and behavioral constraints are strictly separated. Sensitive information (boundaries, dietary restrictions, conflicts) is never brought up as a chat topic. Only the filtered memories are injected; the entire memory store is not dumped into the prompt.

- **🧠 Two-layer memory filtering** -- Capture is permissive (uncertain information may enter the candidate pool), while promotion is strict (confidence tiers + cross-validation + per-user quotas). Filtering happens at the data-backed, auditable, and reversible layer rather than in the prompt: only after filtering in the database does it consume context, and candidates and confidence do not use the conversation budget.

- **🔄 Models are replaceable** -- You can independently choose endpoints for the seven roles: conversation, capability routing, plugin borrowing, session compression, memory consolidation, memory extraction, and image captioning. Local and online endpoints can be combined freely; vector search remains local. Changing models does not touch memories, and changing modes does not require rebuilding the database.

- **🖼 It can see images** -- An optional image-captioning role: when an @-mentioned message contains images, a vision model first turns each image into a one-line description that joins the conversation. Consumer-grade local models rarely offer usable image captioning, so the feature is **off by default** — bind a vision-capable endpoint (a local multimodal model or an online vision API) to enable it; when unbound, behavior is identical to a build without image support.

- **💰 Spending is visible** -- Online token usage is logged daily by role, endpoint, and model. The GUI and `deploy status` show today's usage, **the provider's prefix-cache hit rate** (the only way to verify that the money-saving measure is actually working), and remaining budget. You can set a daily budget; when it is exceeded, memory consolidation is paused by default while **the bot keeps talking in the group as usual**.

### Memory System

- **🔍 Memories need evidence** -- Confidence accumulates only when the same fact is mentioned repeatedly. Statements a user says directly to the Bot count as high-density evidence and can be accepted after a single occurrence. Candidates without new evidence for a long time are automatically discarded.

- **💬 Proactively gather information** -- Information passively ingested from group chats has very low density, so Stella proactively @mentions active users to start a conversation or confirm a memory. Daily quotas, per-user cooldowns, and protection that backs off after consecutive non-responses are provided.

- **🎭 Expression evolves with the group (off by default)** -- The social learning loop: delivery receipts and reply-effect observations distill "which phrasing is worth reusing" and "what this group's slang means". A shadow mode records without intervening first; promoted entries are injected through a budget-controlled prompt slot, and later observations feed back to refine them. Off by default, enabled gradually (`SOCIAL_ENABLED` / `SOCIAL_MODE` — see the [configuration guide](docs/reference/configuration.en.md)).

- **🏠 Shared spaces across groups** -- Multiple QQ groups can belong to one space and share user profiles, long-term memories, and personality. Message tails, topic state, and mute switches remain isolated per group, so Stella will not answer a conversation from group B in group A.

- **🔎 Hybrid search** -- SQLite FTS5 full-text indexing plus multidimensionally weighted ranking, with optional local embedding semantic search and automatic fallback when the service is unavailable.

- **♻️ It forgets** -- Lifetimes are configured by memory type, low-value memories are automatically archived, and long memories are split into atomic facts.

### Engineering

- **🔗 AstrBot plugin compatibility** -- Existing AstrBot plugins can run by placing them in `data/plugins/`, without changing their source code. Plugin card templates are rendered by **local Chromium**, with no external rendering service required.

- **🔌 Extensible** -- Pipeline pre- and post-processing Hooks, with automatic loading from the extension directory.

- **🧪 Verifiable** -- Unit and integration tests cover memory promotion, cross-user isolation, two-layer ownership, anti-fabrication safeguards, routing fallback, and tool isolation. After connecting an online endpoint, there is also a layer of **vendor-neutral contract tests** (an extra field in the request body fails the test; parameter differences may adapt only to error wording and may not use a vendor whitelist) and a prefix-cache guard. Probe scripts also perform regression checks against real models (including a case specifically reproducing "missing information in a noisy environment"), along with a benchmark quantifying four types of routing errors.

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
