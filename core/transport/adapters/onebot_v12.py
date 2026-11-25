# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE。
"""OneBot V12 transport codecs: the cross-platform core protocol.

OneBot V12 events carry the implementation's platform in ``self.platform`` (for
example ``qq`` or ``wechat``), so the platform scope and identity domain come
from each trusted event, never from a hard-coded QQ assumption. User identities
use the ``onebot-v12:<platform>`` domain and are not merged with the legacy
OneBot V11 ``qq:client`` domain.

The module does not import the platform package at import time. No matcher, Bot
connection or startup registration is installed here; callers wire the outbound
side explicitly with ``register_onebot_v12_transport``.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from core.transport.capabilities import AdapterCapabilities
from core.transport.keys import conversation_key_v2, subject_key_v2
from core.transport.message_event import (
    MessageEventV1,
    MessagePartV1,
    MessageRelationV1,
)
from core.transport.models import BotRef, SceneRef, UserRef
from core.transport.normalizers import NormalizedEvent, UnsupportedEvent
from core.transport.outbound import (
    AdapterSendResult,
    DeliveryStatus,
    DeliveryTarget,
    OutboundKind,
    OutboundMessage,
)

ONEBOT_V12_ADAPTER = "onebot-v12"
_ONEBOT_V12_ADAPTER_KEYS = frozenset({"onebotv12"})

# Platform-neutral template; ``platform_scope`` is replaced per target by
# ``OneBotV12CapabilityProvider``. Uploads need the V12 ``upload_file`` flow and
# stay disabled until that flow is implemented and verified.
ONEBOT_V12_CAPABILITIES = AdapterCapabilities(
    adapter=ONEBOT_V12_ADAPTER,
    platform_scope="onebot-v12",
    passive_receive=True,
    private=True,
    group=True,
    channel=True,
    quote=True,
    mention_user=True,
    upload_image=False,
    upload_file=False,
    proactive_send=True,
)

# V12 media segments carry only an implementation-scoped ``file_id``. The part
# records a generic type description; file IDs are not exposed as URLs.
_MEDIA_KINDS = {
    "image": ("image", "image/*"),
    "voice": ("audio", "audio/*"),
    "audio": ("audio", "audio/*"),
    "video": ("video", "video/*"),
    "file": ("file", "application/octet-stream"),
}


def onebot_v12_identity_domain(platform: str) -> str:
    """Return the user identity domain for one OneBot V12 platform."""
    return f"onebot-v12:{platform}"


class OneBotV12CapabilityProvider:
    """Apply the V12 capability template to the target's own platform scope."""

    def __init__(self, capabilities: AdapterCapabilities = ONEBOT_V12_CAPABILITIES) -> None:
        if capabilities.adapter != ONEBOT_V12_ADAPTER:
            raise ValueError("OneBot V12 capability template has the wrong adapter")
        self._capabilities = capabilities

    def capabilities_for(self, target: Any) -> AdapterCapabilities | None:
        bot = getattr(target, "bot", None)
        if getattr(bot, "adapter", None) != ONEBOT_V12_ADAPTER:
            return None
        platform = getattr(bot, "platform_scope", None)
        if not _valid_text(platform):
            return None
        return replace(self._capabilities, platform_scope=platform)


class OneBot12Normalizer:
    """Normalize OneBot V12 private, group and channel message events."""

    def normalize(
        self, bot: Any, event: Any, *, connection_id: str
    ) -> NormalizedEvent | UnsupportedEvent:
        if not _valid_text(connection_id):
            return UnsupportedEvent("connection_id_missing")
        if _adapter_key(_adapter_name(bot)) not in _ONEBOT_V12_ADAPTER_KEYS:
            return UnsupportedEvent("bot_adapter_identity_mismatch")
        if _get(event, "type") != "message":
            return UnsupportedEvent("not_message_event")

        bot_self = _get(event, "self")
        platform = _get(bot_self, "platform")
        self_id = _get(bot_self, "user_id")
        if not _valid_text(platform) or not _valid_text(self_id):
            return UnsupportedEvent("onebot12_bot_identity_missing")
        bot_self_id = _get(bot, "self_id")
        if bot_self_id is not None and str(bot_self_id) != self_id:
            return UnsupportedEvent("onebot12_bot_identity_mismatch")
        bot_platform = _get(bot, "platform")
        if isinstance(bot_platform, str) and bot_platform and bot_platform != platform:
            return UnsupportedEvent("onebot12_bot_platform_mismatch")

        user_id = _get(event, "user_id")
        message_id = _get(event, "message_id")
        if not _valid_text(user_id) or not _valid_text(message_id):
            return UnsupportedEvent("onebot12_message_identity_missing")

        scene = _scene(event, user_id)
        if isinstance(scene, UnsupportedEvent):
            return scene

        occurred_at = _event_time(_get(event, "time"))
        if occurred_at is None:
            return UnsupportedEvent("onebot12_message_timestamp_missing")

        text = _plain_text(event)
        if text is None:
            return UnsupportedEvent("onebot12_message_text_unavailable")

        domain = onebot_v12_identity_domain(platform)
        bot_ref = BotRef(connection_id, ONEBOT_V12_ADAPTER, platform, self_id)
        parts, relations, has_image, mentions_self = _components(
            _segments(event),
            domain=domain,
            self_id=self_id,
            bot_ref=bot_ref,
            scene=scene,
        )
        reply = _get(event, "reply")
        reply_id = _get(reply, "message_id")
        if _valid_text(reply_id) and not any(r.kind == "reply" for r in relations):
            relations.append(_reply_relation(reply_id, bot_ref, scene))
        if not parts:
            return UnsupportedEvent("onebot12_message_has_no_supported_content")

        is_tome = _is_tome(event) or mentions_self or scene.kind == "private"
        message_event = MessageEventV1(
            platform_message_id=message_id,
            occurred_at=occurred_at,
            components=tuple(parts),
            relations=tuple(relations),
        )
        return NormalizedEvent(
            bot_ref=bot_ref,
            user_ref=UserRef(domain, user_id),
            scene_ref=scene,
            text=text,
            platform_message_id=message_id,
            is_tome=is_tome,
            is_self=user_id == self_id,
            has_image=has_image,
            has_segments=True,
            raw_event=event,
            bot_handle=bot,
            message_event=message_event,
        )


onebot12_normalizer = OneBot12Normalizer()


class OneBotV12TargetCodec:
    """Encode exact private, group and channel targets as ``send_message`` params."""

    def encode(self, target: DeliveryTarget, *, bot_handle: Any) -> dict[str, str]:
        if target.target_codec_version != 1:
            raise ValueError("OneBot V12 target codec version is unsupported")
        if target.bot.adapter != ONEBOT_V12_ADAPTER:
            raise ValueError("OneBot V12 target identity mismatch")
        if target.routing_parameters:
            raise ValueError("OneBot V12 target has unsupported routing parameters")
        if _adapter_key(_adapter_name(bot_handle)) not in _ONEBOT_V12_ADAPTER_KEYS:
            raise ValueError("OneBot V12 Bot adapter identity mismatch")
        if str(_get(bot_handle, "self_id")) != target.bot.self_id:
            raise ValueError("OneBot V12 Bot handle self identity mismatch")
        if _get(bot_handle, "platform") != target.bot.platform_scope:
            raise ValueError("OneBot V12 Bot handle platform mismatch")

        scene = target.scene
        if not _valid_text(scene.scene_id) or scene.thread_id is not None:
            raise ValueError("OneBot V12 target scene is invalid")
        if scene.kind == "private" and not scene.parent_path:
            return {"detail_type": "private", "user_id": scene.scene_id}
        if scene.kind == "group" and not scene.parent_path:
            return {"detail_type": "group", "group_id": scene.scene_id}
        if scene.kind == "channel" and len(scene.parent_path) == 1:
            guild_id = scene.parent_path[0]
            if not _valid_text(guild_id):
                raise ValueError("OneBot V12 guild ID is invalid")
            return {
                "detail_type": "channel",
                "guild_id": guild_id,
                "channel_id": scene.scene_id,
            }
        raise ValueError("OneBot V12 target scene kind is unsupported")


class OneBotV12Exporter:
    """Send text, mentions and replies through the exact bound V12 Bot."""

    async def send(
        self,
        target: DeliveryTarget,
        message: OutboundMessage,
        *,
        bot_handle: Any,
        capabilities: AdapterCapabilities,
        encoded_target: dict[str, str],
    ) -> AdapterSendResult:
        if (
            capabilities.adapter != ONEBOT_V12_ADAPTER
            or capabilities.platform_scope != target.bot.platform_scope
        ):
            return AdapterSendResult(
                DeliveryStatus.UNSUPPORTED, error_code="onebot12_capability_identity_mismatch"
            )
        try:
            trusted_target = OneBotV12TargetCodec().encode(target, bot_handle=bot_handle)
        except Exception:
            return AdapterSendResult(
                DeliveryStatus.UNSUPPORTED, error_code="onebot12_target_identity_mismatch"
            )
        if trusted_target != encoded_target:
            return AdapterSendResult(
                DeliveryStatus.UNSUPPORTED, error_code="onebot12_encoded_target_mismatch"
            )
        try:
            from nonebot.adapters.onebot.v12 import Message, MessageSegment
        except ImportError:
            return AdapterSendResult(
                DeliveryStatus.UNSUPPORTED, error_code="onebot12_adapter_unavailable"
            )

        segments: list[Any] = []
        for segment in message.segments:
            if segment.kind is OutboundKind.TEXT:
                if segment.text:
                    segments.append(MessageSegment.text(segment.text))
            elif segment.kind is OutboundKind.AT:
                if encoded_target["detail_type"] != "private":
                    segments.append(MessageSegment.mention(segment.target_id))
            elif segment.kind is OutboundKind.REPLY:
                segments.append(MessageSegment.reply(segment.target_id))
            elif segment.kind is OutboundKind.NATIVE and isinstance(
                segment.native_segment, MessageSegment
            ):
                segments.append(segment.native_segment)
            else:
                return AdapterSendResult(
                    DeliveryStatus.UNSUPPORTED, error_code="onebot12_segment_unsupported"
                )
        if not any(_get(item, "type") != "reply" for item in segments):
            return AdapterSendResult(
                DeliveryStatus.UNSUPPORTED, error_code="onebot12_empty_after_export"
            )

        send_message = _get(bot_handle, "send_message")
        if not callable(send_message):
            return AdapterSendResult(
                DeliveryStatus.UNSUPPORTED, error_code="onebot12_send_api_unavailable"
            )
        try:
            receipt = await send_message(**encoded_target, message=Message(segments))
        except TimeoutError:
            return AdapterSendResult(DeliveryStatus.UNKNOWN, error_code="onebot12_send_timeout")
        except Exception as exc:
            if _is_action_failed(exc):
                return AdapterSendResult(
                    DeliveryStatus.FAILED, error_code="onebot12_action_failed"
                )
            # A network error after the request was written may still have sent it.
            return AdapterSendResult(
                DeliveryStatus.UNKNOWN, error_code="onebot12_send_outcome_unknown"
            )

        message_id = _get(receipt, "message_id")
        if not _valid_text(message_id):
            return AdapterSendResult(
                DeliveryStatus.UNKNOWN, error_code="onebot12_receipt_id_missing"
            )
        return AdapterSendResult(DeliveryStatus.ACCEPTED, (message_id,))


def register_onebot_v12_transport(registry: Any) -> None:
    """Register the V12 exporter with a platform-following capability provider."""
    if registry.binding_for(ONEBOT_V12_ADAPTER) is not None:
        return
    registry.register_exporter(
        ONEBOT_V12_ADAPTER,
        OneBotV12Exporter(),
        ONEBOT_V12_CAPABILITIES,
        target_codec=OneBotV12TargetCodec(),
        capability_provider=OneBotV12CapabilityProvider(),
    )


def _scene(event: Any, user_id: str) -> SceneRef | UnsupportedEvent:
    detail_type = _get(event, "detail_type")
    if detail_type == "private":
        return SceneRef("private", user_id)
    if detail_type == "group":
        group_id = _get(event, "group_id")
        if not _valid_text(group_id):
            return UnsupportedEvent("onebot12_group_identity_missing")
        return SceneRef("group", group_id)
    if detail_type == "channel":
        guild_id = _get(event, "guild_id")
        channel_id = _get(event, "channel_id")
        if not _valid_text(guild_id) or not _valid_text(channel_id):
            return UnsupportedEvent("onebot12_channel_identity_missing")
        return SceneRef("channel", channel_id, parent_path=(guild_id,))
    return UnsupportedEvent("onebot12_detail_type_unsupported")


def _components(
    segments: tuple[Any, ...],
    *,
    domain: str,
    self_id: str,
    bot_ref: BotRef,
    scene: SceneRef,
) -> tuple[list[MessagePartV1], list[MessageRelationV1], bool, bool]:
    parts: list[MessagePartV1] = []
    relations: list[MessageRelationV1] = []
    has_image = False
    mentions_self = False
    for segment in segments:
        kind = _segment_type(segment)
        data = _segment_data(segment)
        if kind == "text":
            text = data.get("text")
            if isinstance(text, str) and text:
                parts.append(MessagePartV1("text", text=text))
        elif kind == "mention":
            target = data.get("user_id")
            if not _valid_text(target):
                parts.append(MessagePartV1("unsupported"))
                continue
            subject = subject_key_v2(domain, target)
            parts.append(MessagePartV1("mention", subject_key=subject))
            relations.append(MessageRelationV1("mention", subject_key=subject))
            mentions_self = mentions_self or target == self_id
        elif kind in _MEDIA_KINDS:
            part_kind, mime_type = _MEDIA_KINDS[kind]
            parts.append(MessagePartV1(part_kind, mime_type=mime_type))
            has_image = has_image or part_kind == "image"
        elif kind == "reply":
            target_message = data.get("message_id")
            if _valid_text(target_message):
                relations.append(_reply_relation(target_message, bot_ref, scene))
        else:
            # mention_all, location and extension segments keep their position
            # without inventing semantics for them.
            parts.append(MessagePartV1("unsupported"))
    return parts, relations, has_image, mentions_self


def _reply_relation(message_id: str, bot_ref: BotRef, scene: SceneRef) -> MessageRelationV1:
    return MessageRelationV1(
        kind="reply",
        target_message_id=message_id,
        target_connection_id=bot_ref.connection_id,
        target_conversation_key=conversation_key_v2(bot_ref, scene),
        resolved=False,
    )


def _get(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    try:
        return getattr(value, name, None)
    except Exception:
        return None


def _valid_text(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return False
    return not any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)


def _adapter_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(char.lower() for char in value if char.isalnum())


def _adapter_name(bot_handle: Any) -> Any:
    getter = _get(_get(bot_handle, "adapter"), "get_name")
    try:
        return getter() if callable(getter) else ""
    except Exception:
        return ""


def _event_time(value: Any) -> datetime | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        # The V12 standard defines ``time`` as a Unix timestamp, i.e. UTC.
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _plain_text(event: Any) -> str | None:
    getter = _get(event, "get_plaintext")
    if not callable(getter):
        return None
    try:
        text = getter()
    except Exception:
        return None
    return text if isinstance(text, str) else None


def _segments(event: Any) -> tuple[Any, ...]:
    message = _get(event, "original_message") or _get(event, "message")
    try:
        return tuple(message) if message is not None else ()
    except TypeError:
        return ()


def _segment_type(segment: Any) -> str:
    kind = _get(segment, "type")
    return kind if isinstance(kind, str) else ""


def _segment_data(segment: Any) -> dict:
    data = _get(segment, "data")
    return data if isinstance(data, dict) else {}


def _is_action_failed(exc: Exception) -> bool:
    return any(
        cls.__name__ == "ActionFailed"
        and cls.__module__.startswith("nonebot.adapters.onebot")
        for cls in type(exc).__mro__
    )


def _is_tome(event: Any) -> bool:
    predicate = _get(event, "is_tome")
    if not callable(predicate):
        return False
    try:
        return bool(predicate())
    except Exception:
        return False


__all__ = [
    "ONEBOT_V12_ADAPTER",
    "ONEBOT_V12_CAPABILITIES",
    "OneBot12Normalizer",
    "OneBotV12CapabilityProvider",
    "OneBotV12Exporter",
    "OneBotV12TargetCodec",
    "onebot12_normalizer",
    "onebot_v12_identity_domain",
    "register_onebot_v12_transport",
]
