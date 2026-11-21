# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，详见项目根目录 LICENSE。
"""阶段2 截断按行拆分重试（2026-11-21 写侧 0 晋升诊断）。

截断直接回退阶段1 候选时，候选不带 verification_contract，晋升门必然
contract_missing。拆分重试让小批次仍能产出带合同的候选。
"""

import asyncio
import json

import memory.consolidator as consolidator
from memory.consolidator import MemoryConsolidator


def _cons(monkeypatch, responder):
    calls: list[str] = []

    async def call(backend, prompt, *, context=None, detailed=False):
        lines = [ln for ln in prompt.split("\n") if ln.startswith("用户(")]
        calls.append("\n".join(lines))
        return responder(lines)

    monkeypatch.setattr(consolidator, "execute_model_call", call)
    monkeypatch.setattr(consolidator, "budget_blocked", lambda role: None)
    monkeypatch.setattr(consolidator, "append_consolidation_log", lambda entry: None)
    cons = MemoryConsolidator.__new__(MemoryConsolidator)
    cons._extract_backend = ("fake", object())  # type: ignore[assignment]
    return cons, calls


def _ok(lines):
    cands = [{"content": ln.split(": ", 1)[1]} for ln in lines]
    return json.dumps({"memory_candidates": cands}, ensure_ascii=False), "stop"


MESSAGES = "\n".join(f"用户({i}): 第{i}条" for i in range(1, 5))


def test_truncated_batch_is_split_and_merged(monkeypatch):
    # 4 行整批截断，2 行一批成功
    cons, calls = _cons(monkeypatch, lambda lines: ("{", "length") if len(lines) > 2 else _ok(lines))
    got = asyncio.run(cons._extract_candidates(1, MESSAGES))
    assert [c["content"] for c in got] == ["第1条", "第2条", "第3条", "第4条"]
    assert len(calls) == 3  # 整批 1 次 + 两半各 1 次
    # 两半不重叠：每条消息只被成功提取一次
    assert calls[1].count("用户(") + calls[2].count("用户(") == 4


def test_still_truncated_at_max_depth_falls_back(monkeypatch):
    cons, calls = _cons(monkeypatch, lambda lines: ("{", "length"))
    assert asyncio.run(cons._extract_candidates(1, MESSAGES)) is None
    # depth 0 → 1 → 2：首个分支拆到底仍截断即停止，不再继续调用
    assert len(calls) == 3


def test_single_line_truncation_falls_back_without_split(monkeypatch):
    cons, calls = _cons(monkeypatch, lambda lines: ("{", "length"))
    assert asyncio.run(cons._extract_candidates(1, "用户(1): 只有一条")) is None
    assert len(calls) == 1


def test_split_retry_respects_budget(monkeypatch):
    cons, calls = _cons(monkeypatch, lambda lines: ("{", "length") if len(lines) > 2 else _ok(lines))
    state = {"n": 0}

    def blocked(role):
        state["n"] += 1
        return "exhausted" if state["n"] > 1 else None  # 首次放行，拆分重试时被拦

    monkeypatch.setattr(consolidator, "budget_blocked", blocked)
    assert asyncio.run(cons._extract_candidates(1, MESSAGES)) is None
    assert len(calls) == 1
