# NoneBot 平台适配器

中文 | [English](platforms.en.md) · [使用指南](README.md) · [文档总览](../README.md)

Stella 使用 NoneBot 适配器连接聊天平台。NoneBot 将适配器包安装与运行时注册分开：已安装的包不会自动启用；Stella 只注册「平台」页中已选择的模块，并在保存后重启生效。NoneBot 也支持在同一 Bot 中注册多个适配器，具体能力取决于各适配器与平台服务。

## 目录与安装

> **核心支持范围：** Stella 核心只支持 OneBot V11 与 OneBot V12（V12 为**实验性功能**，经传输中立入口接入，需显式登记连接，见下文 [OneBot V12](#onebot-v12)）。其他目录适配器在核心中已短路：发行包不随安装包提供，平台页显示为不可添加，启动时跳过并记录警告。其他平台的适配计划在独立项目中开发与维护。决定见 [#134](https://github.com/Enoa-devteam/stella_project/issues/134)。
>
> **协议方向：** OneBot V12 将成为 Stella 的主要适配协议，用于满足广泛的跨平台接入需求；OneBot V11 现有实现暂时保留。

平台页内置的目录快照基于 [NoneBot 官方适配器目录](https://raw.githubusercontent.com/nonebot/nonebot2/master/assets/adapters.json5)，共有 32 条记录，但只有 OneBot V11 与 OneBot V12 可以选择。两者共用 `nonebot-adapter-onebot`，这是 `requirements.txt` 与 `pyproject.toml` 中唯一声明的适配器发行包，随 Docker、在线/离线 Windows 安装器和源码安装一同安装。其他目录项在平台页显示为不可添加；Walle-Q、NTChat 和 Mail 另因依赖冲突被屏蔽，详情见下表。

协议端地址、访问令牌与平台侧权限仍由各协议端项目文档定义；NoneBot 的 `DRIVER` 是全局设置，可从任一已选适配器的「运行时配置」窗口编辑，并对所有已选适配器生效。安装包不会替你创建平台账号或自动启用适配器。

## 已屏蔽的适配器

| 目录项 | 模块 | 原因 |
| --- | --- | --- |
| Walle-Q | `nonebot_adapter_walleq` | 上游 0.2.0 发布于 2023-04-10，并要求 `nonebot-adapter-onebot~=2.2.2`；Stella 核心要求 `nonebot-adapter-onebot>=2.4.6`，约束无法同时满足。参见 [PyPI 元数据](https://pypi.org/pypi/nonebot-adapter-walleq/0.2.0/json)。 |
| NTChat | `nonebot.adapters.ntchat` | 上游 0.3.5 发布于 2023-02-03，并固定 `httpx==0.23.0`；Stella 核心要求 `httpx>=0.24.0`。参见 [PyPI 元数据](https://pypi.org/pypi/nonebot-adapter-ntchat/0.3.5/json)。 |
| Mail | `nonebot.adapters.mail` | 唯一发布版 1.0.0a7 于 2025-01-04 上传，要求 `aiosmtplib~=3.0`；该范围仍含安全公告影响版本，修复版从 5.1.2 起，无法同时满足。参见 [PyPI 元数据](https://pypi.org/pypi/nonebot-adapter-mail/1.0.0a7/json) 与 [安全公告](https://osv.dev/vulnerability/PYSEC-2026-3805)。 |

这三个模块不随 Stella 安装包安装；运行时注册器也会跳过它们并记录日志。若升级前的 `.env` 仍列出其中之一，「平台」页会保留可见的旧配置并提示移除；删除对应卡片后保存即可清理。手工环境变量中的同名模块同样不会被注册。

## 接入步骤

1. 在「平台 → 添加适配器」中搜索并选择一个或多个可用平台。存在未修复的上游安全依赖时，目录项会被隐藏并由运行时策略拒绝。
2. 点击已选卡片的「运行时配置」，在悬浮窗口填写按适配器项目文档预设的字段。支持多账号的适配器可在表单中添加多条 Bot 配置；扩展字段收在「高级环境变量」中。旧版未关联环境变量会保留在未分配分组中，可再指定所属卡片。
3. 按协议端项目的安装/连接说明配置账号、凭据和平台侧权限。
4. 关闭窗口返回页面草稿，使用页面底部保存按钮统一写入本机 `.env`，再重启 Stella。启动日志会列出已注册适配器；缺包、模块导入或 Driver 注册错误会给出对应模块路径。

目录收录只表示可在页面选择和尝试装配，不代表已通过 Stella 行为兼容、真实平台收发或账号验收；OneBot V12 的验收状态见下文。协议端文档与版本要求可能随上游变化，配置前请打开卡片里的项目主页核对。

表单中的敏感字段在读取时脱敏，提交空白凭据会保留原值。

## OneBot V12

> **实验性功能：** OneBot V12 接入尚未在真实协议端上验证。OneBot V11 原生面向 QQ，现有 QQ 链路以 V11 为准；V12 用于进一步适配 QQ 以外的平台，需等待其他平台的 OneBot V12 协议端实现完善后，才能进一步验证其能否正确运行。在此之前，生产环境请继续使用 OneBot V11。已知缺口与验收清单见 [#186](https://github.com/Enoa-devteam/stella_project/issues/186)。

OneBot V12 是面向跨平台的核心协议。它不走 OneBot V11 的 QQ 专用网关，而是经传输中立入口（`TransportIngress`）处理：可信标准化、会话策略、V2 会话登记、消息采集、一次运行时轮次，再按封存的投递计划经出站服务回复。

### 接入

1. 在「平台 → 添加适配器」选择 OneBot V12，在「运行时配置」填写协议端地址：正向 WebSocket 填 `ONEBOT_V12_WS_URLS`，HTTP 填 `ONEBOT_V12_API_ROOTS`；协议端反向 WebSocket 连接 `/onebot/v12/ws`。设置了访问令牌时填写 `ONEBOT_V12_ACCESS_TOKEN`。
2. 在 WebUI 配置页的 `STELLA_TRANSPORT_SETTINGS_JSON` 专用字段为**每个** V12 Bot 登记一条连接。未登记的 Bot 连接时会记录警告，其消息被忽略。

```json
{
  "version": 1,
  "connections": [
    {
      "connection_id": "6f1c2a4e-8b3d-4c5e-9f70-1a2b3c4d5e6f",
      "adapter": "onebot-v12",
      "platform_scope": "wechat",
      "self_id": "wxid_example",
      "enabled": true
    }
  ],
  "defaults": {"llm_enabled": true, "capture_enabled": true, "wake_mode": "mention"},
  "profiles": [],
  "bindings": [],
  "platform_templates": {}
}
```

- `connection_id`：自取的规范 UUID，作为该连接的稳定身份。
- `platform_scope`：协议端在事件 `self.platform` 中上报的平台名（如 `wechat`、`qq`）；`self_id`：事件 `self.user_id`。两者必须与实际事件一致，否则事件被拒绝。
- 策略默认值为 `llm_enabled: false`、`capture_enabled: false`：不开启时既不回复也不记录历史。`wake_mode` 为 `mention` 时，群与频道需 @ Bot，私聊直接触发。

### 身份与当前范围

- 用户身份域为 `onebot-v12:<platform>`，与 OneBot V11 的 `qq:client` 不合并：同一 QQ 账号经 V11 与经 V12 视为不同用户，记忆不互通。
- 已支持：私聊、群、频道（`guild_id` 作为父级）消息的接收与回复；回复包含文本、群/频道首段引用原消息；入站与已确认送达的 Bot 台词进入会话历史；连接的 Bot 绑定到出站注册表。
- 尚不支持（仍只在 OneBot V11 提供）：图片/文件上传与识图（V12 只提供 `file_id`，不解析为媒体）、AstrBot 插件、斜杠/称呼/开关/能力/定时命令、主动发言与群插话参与、链路心跳监测。
- 验收状态：单元与集成测试覆盖标准化、出站编码与入口投递；尚未对真实 OneBot V12 协议端完成收发验收（实验性，见 [#186](https://github.com/Enoa-devteam/stella_project/issues/186)）。

## 官方文档

- [NoneBot：适配器商店内容安装](https://nonebot.dev/docs/tutorial/store)
- [NoneBot：使用与注册适配器](https://nonebot.dev/docs/advanced/adapter)
- [NoneBot 官方目录快照源](https://raw.githubusercontent.com/nonebot/nonebot2/master/assets/adapters.json5)
- [WebUI 管理](webui.md)
