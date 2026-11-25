# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE。
"""OneBot V12 entry point on the transport-neutral ingress.

OneBot V12 is the cross-platform core protocol. Unlike the legacy OneBot V11
gateway, this entry point owns no platform-specific chat logic: every event goes
through ``TransportIngress`` (trusted normalization, policy, V2 conversation
registration, capture and one runtime turn), and replies leave through the
sealed delivery plan and ``OutboundService``.

Only explicitly configured connections are admitted. Each V12 Bot needs an entry
in ``STELLA_TRANSPORT_SETTINGS_JSON`` with ``adapter: "onebot-v12"`` and the
Bot's ``platform_scope`` and ``self_id``; unconfigured Bots are ignored with a
warning on connect. V11 handlers in ``ai_gateway`` annotate OneBot V11 types,
so NoneBot never dispatches V12 events to them.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nonebot import get_driver, logger, on_message
from nonebot.adapters.onebot.v12 import Bot as OneBotV12Bot
from nonebot.adapters.onebot.v12 import MessageEvent as OneBotV12MessageEvent

from core.context import ChatContext
from core.transport.adapters.onebot_v12 import (
    ONEBOT_V12_ADAPTER,
    onebot12_normalizer,
    register_onebot_v12_transport,
)
from core.transport.ingress import IngressResult, TransportIngress, sqlite_v2_registrar
from core.transport.models import BotRef
from core.transport.outbound import (
    DeliveryTarget,
    OutboundMessage,
    OutboundSegment,
    get_outbound_service,
)
from stella_bootstrap.transport_settings import (
    TransportSettingsError,
    TransportSettingsV1,
    parse_transport_settings_json,
)

_SUPPRESSED_DISPOSITIONS = frozenset({"suppressed", "skip", "silent"})
# Same tier as the V11 chat handler; V11 handlers never receive V12 events.
_PRIORITY_ONEBOT_V12 = 3


def configured_connection(
    settings: TransportSettingsV1, bot: Any
) -> BotRef | None:
    """Return the enabled connection configured for this exact V12 Bot."""
    self_id = str(getattr(bot, "self_id", "") or "")
    platform = str(getattr(bot, "platform", "") or "")
    if not self_id or not platform:
        return None
    for connection in settings.connections:
        if (
            connection.adapter == ONEBOT_V12_ADAPTER
            and connection.self_id == self_id
            and connection.platform_scope == platform
            and connection.enabled
        ):
            return BotRef(
                connection.connection_id,
                connection.adapter,
                connection.platform_scope,
                connection.self_id,
            )
    return None


class _SharedRuntime:
    """Submit transport turns through the shared facade with the chat deadline."""

    async def submit_turn(self, key: str, pipeline: object, ctx: ChatContext) -> ChatContext:
        from config import LLM_TIMEOUT
        from core.runtime.facade import new_turn_deadline
        from core.transport.legacy_ingress import shared_legacy_ingress

        if ctx.turn_deadline is None:
            ctx.turn_deadline = new_turn_deadline()
        return await shared_legacy_ingress.submit_turn(
            key,
            pipeline,
            ctx,
            deadline=LLM_TIMEOUT,
            turn_deadline=ctx.turn_deadline,
        )


def _capture_gate(_event: Any, _policy: Any) -> object:
    from core.transport.legacy_ingress import shared_legacy_ingress
    from mneme import capture_gate

    return shared_legacy_ingress.capture_allowed(
        shared_legacy_ingress.capture_decision(capture_gate)
    )


async def _capture_writer(ctx: ChatContext, message_event: Any) -> ChatContext:
    from core.transport.legacy_ingress import shared_legacy_ingress
    from mneme import capture_gate
    from mneme.pre_processors import record_message

    # Re-read the gate at write time: a gate closed in between fails closed.
    capture = shared_legacy_ingress.capture_decision(capture_gate)
    return await record_message(ctx, capture=capture, message_event=message_event)


def _memory_connection() -> Any:
    from config import DB_PATH
    from gravitas.dependency_recovery import StorageDomain, connect_sqlite

    return connect_sqlite(StorageDomain.MEMORY, DB_PATH)


def _chat_pipeline(_ctx: ChatContext, _policy: Any) -> object:
    from . import ai_gateway

    return ai_gateway.pipeline


@dataclass
class _IngressState:
    raw: str
    settings: TransportSettingsV1
    ingress: TransportIngress


class OneBotV12Gateway:
    """Route V12 events through ``TransportIngress`` and deliver the turn reply."""

    def __init__(
        self,
        *,
        settings_source: Callable[[], str | None],
        ingress_factory: Callable[[TransportSettingsV1], TransportIngress] | None = None,
        outbound_service: Callable[[], Any] = get_outbound_service,
    ) -> None:
        self._settings_source = settings_source
        self._ingress_factory = ingress_factory or self._default_ingress
        self._outbound_service = outbound_service
        self._state: _IngressState | None = None
        self._invalid_raw: str | None = None
        self._bound: dict[str, BotRef] = {}

    @staticmethod
    def _default_ingress(settings: TransportSettingsV1) -> TransportIngress:
        return TransportIngress(
            settings,
            normalizers={ONEBOT_V12_ADAPTER: onebot12_normalizer},
            register_conversation=sqlite_v2_registrar(_memory_connection),
            capture_gate=_capture_gate,
            capture_writer=_capture_writer,
            runtime_facade=_SharedRuntime(),
            pipeline_factory=_chat_pipeline,
        )

    def _current(self) -> _IngressState | None:
        raw = self._settings_source() or ""
        if self._state is not None and self._state.raw == raw:
            return self._state
        if not raw.strip() or raw == self._invalid_raw:
            return None
        try:
            settings = parse_transport_settings_json(raw)
        except TransportSettingsError as exc:
            self._invalid_raw = raw
            logger.warning(f"[OneBotV12] transport settings are invalid; V12 ingress disabled: {exc}")
            return None
        self._state = _IngressState(raw, settings, self._ingress_factory(settings))
        return self._state

    def connection_for(self, bot: Any) -> BotRef | None:
        state = self._current()
        return None if state is None else configured_connection(state.settings, bot)

    def bind(self, bot: Any) -> BotRef | None:
        """Bind a connected Bot to its configured connection for outbound sends."""
        bot_ref = self.connection_for(bot)
        if bot_ref is None:
            return None
        registry = self._outbound_service().registry
        register_onebot_v12_transport(registry)
        try:
            registry.bind_bot(bot_ref, bot)
        except ValueError as exc:
            logger.warning(f"[OneBotV12] could not bind connection {bot_ref.connection_id}: {exc}")
            return None
        self._bound[bot_ref.connection_id] = bot_ref
        return bot_ref

    def unbind(self, bot: Any) -> None:
        self_id = str(getattr(bot, "self_id", "") or "")
        registry = self._outbound_service().registry
        for connection_id, bot_ref in list(self._bound.items()):
            if bot_ref.self_id == self_id:
                registry.unbind_bot(bot_ref)
                del self._bound[connection_id]

    async def handle_event(self, bot: Any, event: Any) -> IngressResult | None:
        state = self._current()
        if state is None:
            return None
        bot_ref = configured_connection(state.settings, bot)
        if bot_ref is None:
            return None
        if bot_ref.connection_id not in self._bound:
            self.bind(bot)
        result = await state.ingress.handle_event(bot_ref.connection_id, bot, event)
        if result.status == "rejected":
            logger.debug(f"[OneBotV12] event rejected: {result.reason_code}")
        if result.turn_status == "submitted" and result.turn_context is not None:
            await self.deliver(bot, result.turn_context)
        return result

    async def deliver(self, bot: Any, turn: ChatContext) -> str:
        """Seal and send the finalized reply; returns a bounded outcome label."""
        from core.social.contracts import delivered_texts
        from core.social.delivery import DeliveryPlanError, deliver_lines

        from . import ai_gateway

        if getattr(turn, "reply_disposition", "") in _SUPPRESSED_DISPOSITIONS:
            return "suppressed"
        lines = [line for line in (turn.lines or []) if str(line).strip()]
        if not lines or turn.bot_ref is None or turn.scene_ref is None:
            return "empty"
        private = turn.scene_ref.kind == "private"
        target_user = str(
            turn.peer_id if private else (turn.reply_recipient_user_id or turn.user_id)
        )
        try:
            plan = ai_gateway._seal_ctx_delivery_plan(turn, lines, target_user_id=target_user)
        except DeliveryPlanError as exc:
            logger.warning(
                f"[OneBotV12] delivery plan rejected, reply not sent: {exc} "
                f"(trace={turn.trace_id})"
            )
            return "plan_rejected"

        target = DeliveryTarget(turn.bot_ref, turn.scene_ref)
        quote_id = "" if private else str(turn.platform_message_id or "")
        service = self._outbound_service()

        async def send_one(line: str, index: int):
            segments = [OutboundSegment.text_segment(line)]
            if index == 0 and quote_id:
                segments.insert(0, OutboundSegment.reply(quote_id))
            return await service.send(
                target,
                OutboundMessage(tuple(segments)),
                bot_handle=bot,
                deadline=turn.turn_deadline,
            )

        receipts = await deliver_lines(
            plan,
            scope=None,
            trace_id=turn.trace_id,
            turn_id=turn.turn_id,
            send_one=send_one,
            interval_seconds=ai_gateway.SEND_INTERVAL,
            deadline=turn.turn_deadline,
            plan_guard=lambda current: ai_gateway._delivery_plan_is_current(
                turn, current, target_user_id=target_user
            ),
        )
        delivered = delivered_texts(receipts)
        if not delivered:
            logger.warning(f"[OneBotV12] no reply segment delivered (turn={turn.turn_id})")
            return "not_delivered"
        with contextlib.suppress(Exception):
            await ai_gateway._record_bot_lines(
                turn.bot_id,
                turn.storage_session_id,
                delivered,
                origin=turn,
                receipts=receipts,
            )
        return "delivered"


def _configured_settings_json() -> str | None:
    try:
        from config import settings
    except Exception:
        return None
    value = getattr(settings, "STELLA_TRANSPORT_SETTINGS_JSON", None)
    return value if isinstance(value, str) else None


gateway = OneBotV12Gateway(settings_source=_configured_settings_json)

onebot_v12_handler = on_message(priority=_PRIORITY_ONEBOT_V12, block=False)


@onebot_v12_handler.handle()
async def handle_onebot_v12_message(bot: OneBotV12Bot, event: OneBotV12MessageEvent):
    try:
        await gateway.handle_event(bot, event)
    except Exception as exc:
        # Runtime deadline/cancellation errors end this turn without a reply.
        logger.warning(f"[OneBotV12] turn failed: {type(exc).__name__}: {exc}")


_driver = get_driver()


@_driver.on_bot_connect
async def _bind_onebot_v12_bot(bot: OneBotV12Bot) -> None:
    if gateway.bind(bot) is None:
        logger.warning(
            f"[OneBotV12] Bot {bot.self_id} on platform {bot.platform!r} has no enabled "
            "connection in STELLA_TRANSPORT_SETTINGS_JSON; its messages are ignored. "
            'Add a connection with adapter "onebot-v12", this platform_scope and self_id.'
        )


@_driver.on_bot_disconnect
async def _unbind_onebot_v12_bot(bot: OneBotV12Bot) -> None:
    gateway.unbind(bot)


__all__ = ["OneBotV12Gateway", "configured_connection", "gateway"]
