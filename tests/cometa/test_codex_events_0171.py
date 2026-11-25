# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE.
"""M0 复测实录（openai-codex 0.171.0 + 自带 cli-bin，2026-11-25，#164 / #182）。

fixture ``codex_events_0171.jsonl`` 是经 CodexBackend 驱动真实 App Server 的
三条轮次（脱敏：用户目录 → ``C:\\Users\\user``，工作区 → ``C:\\workspace``，
hook 状态文案泛化）：

- ``completed``：无工具问答，增量流 → message_final → usage → turn/completed；
- ``command``：只读沙盒下执行 ``echo m0-probe-ok``，含 hook/*、
  commandExecution/outputDelta、moderationMetadata 等 0.159.2 之后的新通知；
- ``interrupt``：首批事件后 turn_interrupt，turn/completed(status=interrupted)。

这里走**运行时主路径**（typed Notification → notification_to_event）：用 SDK
自带的 ``NOTIFICATION_MODELS`` 把实录 payload 还原成 typed 模型。SDK 是可选依赖，
未安装时跳过（与 test_codex_events.py 的 typed 用例一致）。
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest

from cometa.backends.codex_events import notification_to_event

FIXTURE = Path(__file__).parent / "fixtures" / "codex_events_0171.jsonl"


@pytest.fixture(scope="module")
def scenarios():
    pytest.importorskip("openai_codex")
    from openai_codex.generated.notification_registry import NOTIFICATION_MODELS
    from openai_codex.models import Notification

    grouped: dict[str, list] = defaultdict(list)
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        model = NOTIFICATION_MODELS.get(raw["method"])
        payload = model.model_validate(raw["payload"]) if model is not None else raw["payload"]
        grouped[raw["__scenario__"]].append(
            notification_to_event(Notification(method=raw["method"], payload=payload))
        )
    return grouped


def _kinds(events):
    return [e.kind for e in events]


def test_completed_turn_extracts_final_answer_from_turn_items(scenarios):
    events = scenarios["completed"]
    kinds = _kinds(events)
    assert kinds[-1] == "completed"
    assert events[-1].payload["text"] == "1+1 等于 2。"
    assert kinds.count("message_delta") >= 2, "增量流逐条可见"
    assert kinds.count("message_final") == 1
    assert "usage" in kinds
    assert kinds.index("message_final") > kinds.index("message_delta")


def test_command_turn_records_command_and_completes(scenarios):
    events = scenarios["command"]
    kinds = _kinds(events)
    assert kinds[-1] == "completed"
    assert events[-1].payload["text"] == "m0-probe-ok"
    records = [e for e in events if e.kind == "command_record"]
    assert records, "命令执行必须形成 command_record 证据"
    assert any("echo m0-probe-ok" in json.dumps(e.payload, ensure_ascii=False) for e in records)


def test_notifications_added_after_0159_degrade_to_phase(scenarios):
    """hook/*、moderationMetadata、commandExecution/outputDelta：未知语义 → phase，不臆造。"""
    events = scenarios["command"]
    new = {"hook/started", "hook/completed", "turn/moderationMetadata",
           "item/commandExecution/outputDelta"}
    seen = {e.raw_kind for e in events if e.raw_kind in new}
    assert seen == new
    assert all(e.kind == "phase" for e in events if e.raw_kind in new)


def test_interrupted_turn_is_not_reported_as_success(scenarios):
    events = scenarios["interrupt"]
    kinds = _kinds(events)
    assert kinds[-1] == "interrupted"
    assert "completed" not in kinds and "failed" not in kinds
