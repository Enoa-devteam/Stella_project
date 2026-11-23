# 插件安装

中文 | [English](plugins.en.md) · [文档总览](../README.md)

本页说明如何把现成插件装进 stella。要自己写插件，读 [插件接入规范](../reference/plugin-spec.md)。

## 🔗 装插件（可选）

stella 能直接跑 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 生态的插件，**不用改插件源码**：

```
把插件目录整个放进  data/plugins/<插件名>/
如果插件带 requirements.txt，装一下它的依赖
重启 stella
```

目录名不用改：GitHub「Download ZIP」解出来的 `xxx-master` / `xxx-main` 后缀照样能装。但**压缩包本身要先解压**——`data/plugins/` 下的 `.zip` 不会被加载。

启动后看 `logs/boot_debug.log`，里面会写清发现了哪些插件、加载成功还是失败、失败原因。

## 让工具能被聊天自动调用

插件的 `@command` 指令（默认前缀 `/`）装完就能用。插件用 `@llm_tool` 注册的**函数工具**要能在聊天里被自动调用，还需要一份能力声明——按 [插件接入规范](../reference/plugin-spec.md) 写的插件**自带** `capability.toml`，这种插件装完就是完整的，你什么都不用配。

插件没自带（多数现存的 AstrBot 插件都没有），或者它自带的那份不合你的用法时，就在 `config/capabilities/<域名>.toml` 里补一条 / 覆盖一条——用户目录里的声明优先级最高，同一个工具被它认领后，插件自带的那条整条跳过。仓库里有一份真实样例（`config/capabilities/entertainment.toml`）可以照抄，格式说明见 `config/capabilities/information.toml.example`，怎么写才准见 [插件接入规范 §6.3](../reference/plugin-spec.md#63-怎么写-examples)。

> 为什么需要这份声明：插件的工具描述是写给「看着全部工具做选择」的决策器的指令句，而 stella 的路由是拿它和用户的**问句**算语义相似度——两种用途要求的文本形态不同，直接拿来用会让同类工具互相抢。实测数据与取舍见 [能力系统](../architecture/capability-system.md#声明优先为什么自动派生不参与路由)。

写插件或想确认一份声明写得对不对，跑 `python -m deploy plugin-check <插件目录>`：16 项检查，零 error 才算达标。不想从零手写 examples，可以先跑 `python -m deploy plugin-scaffold <插件目录>` 生成一份草稿（`capability.toml.draft`），它同时用真实 embedding 打一份量化报告告诉你这份语料准不准；草稿要人审、改名并把 `reviewed` 置为 `true` 才会生效——没审过的语料到不了路由。

## 确认插件进了路由

装完想知道它到底进没进路由，三个地方看的是同一份清单：在群里 @ 机器人问一句「你能做什么」、跑 `python -m deploy capabilities`、或者打开 `Stella.exe` 的「插件」页点开这个插件（绿点＝该工具已被声明认领、能被聊天自动触发）。列的都是哪些能力能被聊天自动触发、哪些不能，以及不能的原因（没有声明 / 工具名拼错 / 被更高优先层顶掉 / 实现正在退避）。这比翻启动日志直接。

## 热重载与卡片渲染

调试插件时可以打开热重载（`ASTRBOT_PLUGIN_HOT_RELOAD_ENABLED=true`，**默认关闭**），改完代码在群里发「@stella 重载插件 <插件目录名>」就能不重启生效。它**不等于重启**——裸 `asyncio.create_task` 起的任务、插件起的线程与 monkeypatch 都收不回来，所以怀疑状态不干净就重启，细节见 [插件接入规范 §13](../reference/plugin-spec.md#13-调试)。

插件的卡片图由本地 Chromium 渲染，**首次需要出图时会自动后台下载约 270MB 的浏览器内核**，期间插件照常回纯文本，装好后自动生效、不用重启。
