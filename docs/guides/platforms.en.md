# NoneBot Platform Adapters

[中文](platforms.md) | English · [Usage guides](README.en.md) · [Documentation](../README.en.md)

Stella uses NoneBot adapters to connect to chat platforms. NoneBot separates installing an adapter package from registering it at runtime: an installed package is not enabled automatically. Stella registers only modules selected on the **Platforms** page, after a restart. NoneBot can register multiple adapters in one Bot; actual capabilities depend on each adapter and platform service.

## Catalog and installation

> **Core support scope:** Stella core supports only OneBot V11 and OneBot V12 (V12 is an **experimental feature**; it enters through the transport-neutral ingress and needs an explicitly registered connection; see [OneBot V12](#onebot-v12) below). The other catalog adapters are short-circuited in core: their packages are not shipped with the installers, the Platforms page shows them as unavailable, and boot skips them with a warning. Adapters for other platforms are planned as a separately maintained project. See [#134](https://github.com/Enoa-devteam/stella_project/issues/134) for the decision.
>
> **Protocol direction:** OneBot V12 will become Stella's primary adaptation protocol, covering broad cross-platform connection needs. The existing OneBot V11 implementation is kept for now.

The catalog snapshot in the Platforms page follows the [official NoneBot adapter directory](https://raw.githubusercontent.com/nonebot/nonebot2/master/assets/adapters.json5) and contains 32 entries, but only OneBot V11 and OneBot V12 can be selected. Both use `nonebot-adapter-onebot`, the only adapter distribution declared in `requirements.txt` and `pyproject.toml`; it is installed with Docker, the online/offline Windows installers, and source installations. Other catalog entries are shown as unavailable on the Platforms page; Walle-Q, NTChat, and Mail are additionally blocked by dependency conflicts, see the table below.

Protocol-implementation addresses, access tokens, and platform-side permissions remain defined by each implementation's docs. NoneBot's `DRIVER` is global; edit it from any selected adapter's **Runtime settings** dialog and it applies to all selected adapters. The installer does not create platform accounts or enable adapters automatically.

## Blocked adapters

| Catalog entry | Module | Reason |
| --- | --- | --- |
| Walle-Q | `nonebot_adapter_walleq` | Upstream 0.2.0 was released on 2023-04-10 and requires `nonebot-adapter-onebot~=2.2.2`; Stella core requires `nonebot-adapter-onebot>=2.4.6`, so the constraints cannot be resolved together. See [PyPI metadata](https://pypi.org/pypi/nonebot-adapter-walleq/0.2.0/json). |
| NTChat | `nonebot.adapters.ntchat` | Upstream 0.3.5 was released on 2023-02-03 and pins `httpx==0.23.0`; Stella core requires `httpx>=0.24.0`. See [PyPI metadata](https://pypi.org/pypi/nonebot-adapter-ntchat/0.3.5/json). |
| Mail | `nonebot.adapters.mail` | Its only release, 1.0.0a7, was uploaded on 2025-01-04 and requires `aiosmtplib~=3.0`; the affected range is fixed starting in 5.1.2. See [PyPI metadata](https://pypi.org/pypi/nonebot-adapter-mail/1.0.0a7/json) and the [security advisory](https://osv.dev/vulnerability/PYSEC-2026-3805). |

These packages are not installed by Stella's installers. The runtime registrar skips these modules and logs a warning. If an older `.env` still lists one, the Platforms page keeps it visible and asks you to remove the card; remove it and save to clean up the configuration. The same module paths are skipped when supplied through process environment variables.

## Connect a platform

1. Search for a platform in **Platforms → Add adapter** and select one or more available entries.
2. Choose **Runtime settings** on a selected card. The floating dialog contains fields prefilled from that adapter project's docs. Adapters that support multiple accounts let you add multiple bot entries; less common settings remain under **Advanced environment variables**. Legacy variables without an adapter stay in an unassigned section until you choose a card for them.
3. Follow the protocol implementation's instructions for accounts, credentials, and platform-side permissions.
4. Close the dialog to return to the page draft, use the page-level Save button to write settings to the local `.env`, and restart Stella. Startup logs list registered adapters. Missing packages, import failures, and Driver registration errors identify the relevant module path.

Catalog inclusion only means an adapter is selectable and can be assembled; it does not certify behavior compatibility, live platform delivery, or account acceptance. See below for OneBot V12's acceptance status. Implementation docs and version requirements can change, so review the project page linked from each catalog card.

Secret fields are redacted on read, and submitting them blank preserves their stored values.

## OneBot V12

> **Experimental feature:** OneBot V12 support has not been verified against a real implementation. OneBot V11 was designed natively for QQ, and Stella's QQ path runs on V11. V12 is for adapting Stella to platforms other than QQ, so it can only be verified further once OneBot V12 implementations for those platforms are complete. Until then, keep using OneBot V11 in production. Known gaps and the acceptance checklist are tracked in [#186](https://github.com/Enoa-devteam/stella_project/issues/186).

OneBot V12 is the cross-platform core protocol. It doesn't use the QQ-specific OneBot V11 gateway. Instead, each event goes through the transport-neutral ingress (`TransportIngress`): trusted normalization, conversation policy, V2 conversation registration, message capture and one runtime turn. The reply is sealed into a delivery plan and sent through the outbound service.

### Setup

1. In **Platforms → Add adapter**, select OneBot V12 and fill in the implementation's address under **Runtime settings**: `ONEBOT_V12_WS_URLS` for forward WebSocket, or `ONEBOT_V12_API_ROOTS` for HTTP. For reverse WebSocket, the implementation connects to `/onebot/v12/ws`. If the implementation uses an access token, set `ONEBOT_V12_ACCESS_TOKEN`.
2. In the WebUI configuration page, register a connection for **each** V12 Bot in the dedicated `STELLA_TRANSPORT_SETTINGS_JSON` field. A Bot without a registered connection is logged with a warning on connect, and its messages are ignored.

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

- `connection_id`: a canonical UUID you choose. It is the connection's stable identity.
- `platform_scope`: the platform the implementation reports in each event's `self.platform` (for example `wechat` or `qq`). `self_id`: the event's `self.user_id`. Both must match the actual events, or the events are rejected.
- The policy defaults are `llm_enabled: false` and `capture_enabled: false`. Unless you turn them on, the Bot neither replies nor records history. With `wake_mode: "mention"`, groups and channels need an @ mention, and private messages always trigger.

### Identity and current scope

- User identities use the `onebot-v12:<platform>` domain and are not merged with OneBot V11's `qq:client` domain. The same QQ account connected through V11 and through V12 counts as two different users, and their memories are not shared.
- Supported: receiving and replying to private, group and channel messages (with `guild_id` as the channel's parent). Replies contain text, and in groups and channels the first segment quotes the original message. Inbound messages and confirmed Bot lines go into conversation history. Connected Bots are bound to the outbound registry.
- Not yet supported (OneBot V11 only for now): image and file upload and image understanding (V12 only provides a `file_id`, which isn't resolved to media), AstrBot plugins, slash, addressing, toggle, capability and scheduling commands, proactive speech and group participation, and link heartbeat monitoring.
- Acceptance status: unit and integration tests cover normalization, outbound encoding and entry-point delivery. Sending and receiving have not been verified against a real OneBot V12 implementation (experimental; see [#186](https://github.com/Enoa-devteam/stella_project/issues/186)).

## Official docs

- [NoneBot: install adapters from the store](https://nonebot.dev/docs/tutorial/store)
- [NoneBot: use and register adapters](https://nonebot.dev/docs/advanced/adapter)
- [Official NoneBot catalog source](https://raw.githubusercontent.com/nonebot/nonebot2/master/assets/adapters.json5)
- [WebUI administration](webui.en.md)
