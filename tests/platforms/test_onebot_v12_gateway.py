# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE。
"""OneBot V12 gateway: real TransportIngress, real V12 events, fake Bot transport."""

from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace

import nonebot
import pytest

pytest.importorskip("nonebot.adapters.onebot.v12")
nonebot.init()
from nonebot.adapters.onebot.v12 import (
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)

from core.social.delivery import delivery_draft_from_context
from core.transport.adapters.onebot_v12 import onebot12_normalizer
from core.transport.ingress import TransportIngress
from core.transport.keys import conversation_key_v2
from core.transport.models import BotRef, ConversationRefV2
from core.transport.outbound import OutboundService, TransportRegistry
from stella_bootstrap.transport_settings import parse_transport_settings_json
from stella_project.plugins.bot_main import ai_gateway
from stella_project.plugins.bot_main.onebot_v12_gateway import (
    OneBotV12Gateway,
    configured_connection,
)

CONNECTION = "12121212-1212-4121-8121-121212121212"
BOT_ID = "wxid_bot"
PLATFORM = "wechat"


class _V12Bot(SimpleNamespace):
    def __init__(self, *, self_id: str = BOT_ID, platform: str = PLATFORM):
        super().__init__(
            self_id=self_id,
            platform=platform,
            adapter=SimpleNamespace(get_name=lambda: "OneBot V12"),
        )
        self.sent: list[dict] = []

    async def send_message(self, **params):
        self.sent.append(params)
        return {"message_id": f"sent-{len(self.sent)}", "time": 1.0}


def _settings_json(*, enabled: bool = True, self_id: str = BOT_ID, adapter: str = "onebot-v12") -> str:
    return json.dumps(
        {
            "version": 1,
            "connections": [
                {
                    "connection_id": CONNECTION,
                    "adapter": adapter,
                    "platform_scope": PLATFORM,
                    "self_id": self_id,
                    "enabled": enabled,
                }
            ],
            "defaults": {"llm_enabled": True, "wake_mode": "mention"},
            "profiles": [],
            "bindings": [],
            "platform_templates": {},
        }
    )


def _event(detail_type: str, message: list[dict], *, user_id: str = "wxid_user", **extra):
    payload = {
        "id": "evt-1",
        "time": 1_764_000_000,
        "type": "message",
        "detail_type": detail_type,
        "sub_type": "",
        "self": {"platform": PLATFORM, "user_id": BOT_ID},
        "message_id": "msg-1",
        "message": message,
        "alt_message": "",
        "user_id": user_id,
        **extra,
    }
    model = GroupMessageEvent if detail_type == "group" else PrivateMessageEvent
    return model.model_validate(payload)


class _ReplyingRuntime:
    """Stand-in for the shared facade: produces a finalized turn with a draft."""

    def __init__(self, lines: list[str]):
        self.lines = lines
        self.calls: list[tuple[str, object]] = []

    async def submit_turn(self, key, pipeline, ctx):
        self.calls.append((key, ctx))
        ctx.trace_id = uuid.uuid4().hex
        ctx.turn_id = uuid.uuid4().hex
        ctx.delivery_source_kind = "model"
        ctx.reply_disposition = "deliver"
        ctx.lines = list(self.lines)
        ctx.delivery_draft = delivery_draft_from_context(ctx)
        return ctx


def _registrar(calls: list):
    def register(bot, scene, memory_space):
        ref = ConversationRefV2(
            bot=bot,
            scene=scene,
            storage_session_id=-100 - len(calls),
            memory_space=memory_space or f"transport:{conversation_key_v2(bot, scene)}",
        )
        calls.append(ref)
        return ref

    return register


@pytest.fixture()
def wiring(monkeypatch):
    from memory import scope_versions

    monkeypatch.setattr(scope_versions, "current_versions_strict", lambda keys: dict.fromkeys(keys, 1))
    monkeypatch.setattr(ai_gateway, "_delivery_plan_is_current", lambda *a, **k: True)
    recorded: list[tuple] = []

    async def record_bot_lines(*args, **kwargs):
        recorded.append((args, kwargs))

    monkeypatch.setattr(ai_gateway, "_record_bot_lines", record_bot_lines)
    monkeypatch.setattr(ai_gateway, "SEND_INTERVAL", 0)
    registrations: list = []
    runtime = _ReplyingRuntime(["你好呀"])
    service = OutboundService(TransportRegistry())

    def ingress_factory(settings):
        return TransportIngress(
            settings,
            normalizers={"onebot-v12": onebot12_normalizer},
            register_conversation=_registrar(registrations),
            runtime_facade=runtime,
            pipeline_factory=lambda *_: object(),
        )

    raw = {"value": _settings_json()}
    gateway = OneBotV12Gateway(
        settings_source=lambda: raw["value"],
        ingress_factory=ingress_factory,
        outbound_service=lambda: service,
    )
    return SimpleNamespace(
        gateway=gateway,
        runtime=runtime,
        service=service,
        registrations=registrations,
        recorded=recorded,
        raw=raw,
    )


def test_configured_connection_requires_exact_enabled_v12_slot():
    settings = parse_transport_settings_json(_settings_json())
    assert configured_connection(settings, _V12Bot()) == BotRef(
        CONNECTION, "onebot-v12", PLATFORM, BOT_ID
    )
    assert configured_connection(settings, _V12Bot(platform="qq")) is None
    assert configured_connection(settings, _V12Bot(self_id="other")) is None
    disabled = parse_transport_settings_json(_settings_json(enabled=False))
    assert configured_connection(disabled, _V12Bot()) is None
    other_adapter = parse_transport_settings_json(_settings_json(adapter="discord"))
    assert configured_connection(other_adapter, _V12Bot()) is None


def test_group_mention_runs_one_turn_and_replies_with_quote(wiring):
    bot = _V12Bot()
    event = _event(
        "group",
        [{"type": "mention", "data": {"user_id": BOT_ID}}, {"type": "text", "data": {"text": " 在吗"}}],
        group_id="room-1",
    )
    result = asyncio.run(wiring.gateway.handle_event(bot, event))

    assert result is not None and result.turn_status == "submitted"
    key, ctx = wiring.runtime.calls[0]
    assert key == wiring.registrations[0].canonical_key
    assert ctx.user_id == "wxid_user"
    assert ctx.adapter_name == "onebot-v12"
    assert ctx.platform_scope == PLATFORM
    assert len(bot.sent) == 1
    sent = bot.sent[0]
    assert sent["detail_type"] == "group" and sent["group_id"] == "room-1"
    assert sent["message"] == Message(
        [MessageSegment.reply("msg-1"), MessageSegment.text("你好呀")]
    )
    assert len(wiring.recorded) == 1
    # Background sends can resolve the exact Bot after the event.
    assert wiring.service.registry.resolve_bot(
        BotRef(CONNECTION, "onebot-v12", PLATFORM, BOT_ID)
    ) is bot


def test_private_message_replies_without_quote(wiring):
    bot = _V12Bot()
    event = _event("private", [{"type": "text", "data": {"text": "hi"}}])
    result = asyncio.run(wiring.gateway.handle_event(bot, event))

    assert result is not None and result.turn_status == "submitted"
    assert bot.sent[0]["detail_type"] == "private"
    assert bot.sent[0]["user_id"] == "wxid_user"
    assert bot.sent[0]["message"] == Message([MessageSegment.text("你好呀")])


def test_group_message_without_mention_does_not_start_a_turn(wiring):
    bot = _V12Bot()
    event = _event("group", [{"type": "text", "data": {"text": "chatter"}}], group_id="room-1")
    result = asyncio.run(wiring.gateway.handle_event(bot, event))

    assert result is not None and result.turn_status != "submitted"
    assert wiring.runtime.calls == []
    assert bot.sent == []


def test_unconfigured_bot_and_missing_settings_are_ignored(wiring):
    event = _event("private", [{"type": "text", "data": {"text": "hi"}}])
    stranger = _V12Bot(self_id="wxid_stranger")
    assert asyncio.run(wiring.gateway.handle_event(stranger, event)) is None

    wiring.raw["value"] = ""
    assert asyncio.run(wiring.gateway.handle_event(_V12Bot(), event)) is None
    assert wiring.runtime.calls == []


def test_invalid_settings_disable_ingress_without_raising(wiring):
    wiring.raw["value"] = "{not json"
    event = _event("private", [{"type": "text", "data": {"text": "hi"}}])
    assert asyncio.run(wiring.gateway.handle_event(_V12Bot(), event)) is None


def test_suppressed_reply_is_not_sent(wiring):
    wiring.runtime.lines = []
    bot = _V12Bot()
    event = _event("private", [{"type": "text", "data": {"text": "hi"}}])
    asyncio.run(wiring.gateway.handle_event(bot, event))

    assert bot.sent == []


def test_unbind_releases_the_exact_bot(wiring):
    bot = _V12Bot()
    assert wiring.gateway.bind(bot) == BotRef(CONNECTION, "onebot-v12", PLATFORM, BOT_ID)
    wiring.gateway.unbind(bot)

    assert wiring.service.registry.resolve_bot(
        BotRef(CONNECTION, "onebot-v12", PLATFORM, BOT_ID)
    ) is None
