# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE。
"""OneBot V12 normalizer contract against the locked adapter's event models."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

pytest.importorskip("nonebot.adapters.onebot.v12")
from nonebot.adapters.onebot.v12 import (
    ChannelMessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from core.transport.adapters.onebot_v12 import (
    ONEBOT_V12_ADAPTER,
    OneBot12Normalizer,
    OneBotV12CapabilityProvider,
    onebot_v12_identity_domain,
)
from core.transport.keys import conversation_key_v2, subject_key_v2
from core.transport.models import BotRef, SceneRef, UserRef
from core.transport.normalizers import NormalizedEvent, UnsupportedEvent

BOT_ID = "bot-self"
CONNECTION = "ob12-wechat"
TIMESTAMP = 1_764_000_000


def _bot(*, self_id: str = BOT_ID, platform: str = "wechat", adapter: str = "OneBot V12"):
    return SimpleNamespace(
        self_id=self_id,
        platform=platform,
        adapter=SimpleNamespace(get_name=lambda: adapter),
    )


def _base(detail_type: str, message: list[dict], **extra) -> dict:
    return {
        "id": "evt-1",
        "time": TIMESTAMP,
        "type": "message",
        "detail_type": detail_type,
        "sub_type": "",
        "self": {"platform": "wechat", "user_id": BOT_ID},
        "message_id": "msg-1",
        "message": message,
        "alt_message": "",
        "user_id": "user-7",
        **extra,
    }


def _text(text: str) -> dict:
    return {"type": "text", "data": {"text": text}}


def _normalize(event, *, bot=None):
    return OneBot12Normalizer().normalize(bot or _bot(), event, connection_id=CONNECTION)


def test_group_message_uses_event_platform_and_v12_identity_domain():
    event = GroupMessageEvent.model_validate(
        _base("group", [_text("hello")], group_id="group-9")
    )
    result = _normalize(event)

    assert isinstance(result, NormalizedEvent)
    assert result.bot_ref == BotRef(CONNECTION, ONEBOT_V12_ADAPTER, "wechat", BOT_ID)
    assert result.user_ref == UserRef("onebot-v12:wechat", "user-7")
    assert result.scene_ref == SceneRef("group", "group-9")
    assert result.text == "hello"
    assert result.platform_message_id == "msg-1"
    assert not result.is_tome
    assert not result.is_self
    assert result.message_event is not None
    assert result.message_event.event_kind == "create"
    assert result.message_event.occurred_at == datetime.fromtimestamp(TIMESTAMP, tz=timezone.utc)
    assert [part.kind for part in result.message_event.components] == ["text"]


def test_identity_domain_is_not_the_legacy_qq_domain():
    assert onebot_v12_identity_domain("qq") == "onebot-v12:qq"
    assert onebot_v12_identity_domain("qq") != "qq:client"


def test_private_message_is_addressed_to_the_bot():
    event = PrivateMessageEvent.model_validate(_base("private", [_text("hi")]))
    result = _normalize(event)

    assert isinstance(result, NormalizedEvent)
    assert result.scene_ref == SceneRef("private", "user-7")
    assert result.is_tome


def test_channel_message_keeps_guild_as_parent_path():
    event = ChannelMessageEvent.model_validate(
        _base("channel", [_text("hey")], guild_id="guild-1", channel_id="chan-2")
    )
    result = _normalize(event)

    assert isinstance(result, NormalizedEvent)
    assert result.scene_ref == SceneRef("channel", "chan-2", parent_path=("guild-1",))


def test_self_mention_marks_tome_and_records_mention_relation():
    event = GroupMessageEvent.model_validate(
        _base(
            "group",
            [{"type": "mention", "data": {"user_id": BOT_ID}}, _text(" ping")],
            group_id="group-9",
        )
    )
    result = _normalize(event)

    assert isinstance(result, NormalizedEvent)
    assert result.is_tome
    subject = subject_key_v2("onebot-v12:wechat", BOT_ID)
    kinds = [part.kind for part in result.message_event.components]
    assert kinds == ["mention", "text"]
    assert result.message_event.components[0].subject_key == subject
    assert any(
        relation.kind == "mention" and relation.subject_key == subject
        for relation in result.message_event.relations
    )


def test_media_reply_and_unknown_segments_are_described_safely():
    event = GroupMessageEvent.model_validate(
        _base(
            "group",
            [
                {"type": "reply", "data": {"message_id": "older-1", "user_id": "u"}},
                {"type": "image", "data": {"file_id": "https://cdn.example/secret?token=x"}},
                {"type": "location", "data": {"latitude": 1.0, "longitude": 2.0, "title": "", "content": ""}},
            ],
            group_id="group-9",
        )
    )
    result = _normalize(event)

    assert isinstance(result, NormalizedEvent)
    assert result.has_image
    components = result.message_event.components
    assert [part.kind for part in components] == ["image", "unsupported"]
    assert components[0].mime_type == "image/*"
    assert components[0].attachment_ref is None
    reply = [r for r in result.message_event.relations if r.kind == "reply"]
    assert len(reply) == 1
    assert reply[0].target_message_id == "older-1"
    assert reply[0].target_conversation_key == conversation_key_v2(
        result.bot_ref, result.scene_ref
    )


def test_self_echo_is_flagged():
    data = _base("group", [_text("echo")], group_id="group-9")
    data["user_id"] = BOT_ID
    result = _normalize(GroupMessageEvent.model_validate(data))

    assert isinstance(result, NormalizedEvent)
    assert result.is_self


@pytest.mark.parametrize(
    ("bot", "reason"),
    [
        (_bot(adapter="OneBot V11"), "bot_adapter_identity_mismatch"),
        (_bot(self_id="someone-else"), "onebot12_bot_identity_mismatch"),
        (_bot(platform="qq"), "onebot12_bot_platform_mismatch"),
    ],
)
def test_bot_identity_mismatches_fail_closed(bot, reason):
    event = GroupMessageEvent.model_validate(
        _base("group", [_text("x")], group_id="group-9")
    )
    result = _normalize(event, bot=bot)

    assert result == UnsupportedEvent(reason)


def test_missing_connection_and_non_message_events_are_rejected():
    event = GroupMessageEvent.model_validate(
        _base("group", [_text("x")], group_id="group-9")
    )
    assert OneBot12Normalizer().normalize(_bot(), event, connection_id="") == UnsupportedEvent(
        "connection_id_missing"
    )
    notice = SimpleNamespace(type="notice")
    assert _normalize(notice) == UnsupportedEvent("not_message_event")


def test_capability_provider_follows_target_platform():
    provider = OneBotV12CapabilityProvider()
    target = SimpleNamespace(bot=BotRef(CONNECTION, ONEBOT_V12_ADAPTER, "wechat", BOT_ID))
    capabilities = provider.capabilities_for(target)

    assert capabilities is not None
    assert capabilities.platform_scope == "wechat"
    assert capabilities.group and capabilities.private and capabilities.channel
    assert not capabilities.upload_image
    other = SimpleNamespace(bot=BotRef("legacy-qq:1", "onebot-v11", "qq", "1"))
    assert provider.capabilities_for(other) is None
