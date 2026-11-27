# Installing Plugins

[中文](plugins.md) | English · [Documentation](../README.en.md)

This page covers installing existing plugins into stella. To write your own, read the [Plugin Integration Specification](../reference/plugin-spec.en.md).

## 🔗 Installing plugins (optional)

stella can run plugins from the [AstrBot](https://github.com/AstrBotDevs/AstrBot) ecosystem directly, **without changing plugin source code**:

```
Place the entire plugin directory in  data/plugins/<plugin-name>/
If the plugin includes requirements.txt, install its dependencies
Restart stella
```

The directory name does not need to be changed: an `xxx-master` / `xxx-main` suffix extracted by GitHub's "Download ZIP" works as-is. However, **the archive itself must be extracted first**; `.zip` files under `data/plugins/` will not be loaded.

After startup, check `logs/boot_debug.log`. It records which plugins were found, whether loading succeeded or failed, and the reason for any failure.

## Letting chat call a plugin's tools

Plugin `@command` commands (default prefix `/`) work immediately after installation. Function tools registered with `@llm_tool` additionally need a capability declaration before chat can trigger them -- and a plugin written to the [Plugin Integration Specification](../reference/plugin-spec.en.md) **ships its own** `capability.toml`, so that kind of plugin is complete on arrival and needs no configuration from you.

When a plugin ships none (most existing AstrBot plugins do not), or the one it ships does not suit how you use it, add or override an entry in `config/capabilities/<domain>.toml` -- declarations in the user directory have the highest precedence, and once one of them claims a tool the plugin's own entry is skipped entirely. The repository contains a real example (`config/capabilities/entertainment.toml`) that you can copy; see `config/capabilities/information.toml.example` for the format, and [Plugin Integration Specification §6.3](../reference/plugin-spec.en.md#63-how-to-write-examples) for how to write one that actually routes.

> Why the declaration is needed: a plugin's tool description is an instruction sentence for a decision-maker that chooses while looking at all tools, whereas stella's router calculates semantic similarity between it and the user's **question**. The two purposes require different text forms, and using the description directly makes similar tools compete with one another. See [Capability System](../architecture/capability-system.en.md#declaration-priority-why-automatically-derived-capabilities-do-not-participate-in-routing) for measured data and the trade-offs.

Writing a plugin, or unsure whether a declaration is right? Run `python -m deploy plugin-check <plugin dir>`: 16 checks, and zero errors is the bar. If you would rather not write `examples` from scratch, run `python -m deploy plugin-scaffold <plugin dir>` first to generate a draft (`capability.toml.draft`); it also computes a quantified report with the real embedding model telling you how well that corpus actually routes. The draft needs a human review, a rename, and `reviewed = true` before it takes effect -- unreviewed corpus never reaches the Router.

## Confirming a plugin reached routing

To see whether it actually made it into the routing set, three places print the same list: @-mention the bot in a group and ask "what can you do", run `python -m deploy capabilities`, or open the "Extensions" page of `Stella.exe` and click the plugin (a green dot means a declaration has claimed that tool, so chat can trigger it automatically). All of them show which capabilities chat can trigger automatically, which cannot, and why not (no declaration / misspelled tool name / claimed by a higher tier / implementation backing off). Quicker than reading the boot log.

## Hot reload and card rendering

While developing a plugin you can turn on hot reload (`ASTRBOT_PLUGIN_HOT_RELOAD_ENABLED=true`, **off by default**) and pick up code changes without a restart by sending "@stella 重载插件 &lt;plugin directory&gt;" in a group. It is **not a restart** — tasks started with a bare `asyncio.create_task`, threads a plugin started and monkeypatches are not reclaimed, so restart whenever you suspect the state is unclean. Details in [Plugin Specification §13](../reference/plugin-spec.en.md#13-debugging).

Plugin cards are rendered by local Chromium. **The first time an image is needed, it automatically downloads about 270 MB of browser engine in the background**; the plugin continues to return plain text during the download, and takes effect automatically once installation finishes without requiring a restart.
