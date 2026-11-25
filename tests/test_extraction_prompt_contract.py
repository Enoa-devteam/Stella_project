# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 Stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，详见项目根目录 LICENSE。
"""EXTRACTION_PROMPT 契约硬规则块的结构守卫。

2026-10-17 live 回放实证：阶段2 候选契约全 unknown、0 accepted，根因是提示词
没教模型产出闸门（memory/evidence_contract.py）能接受的契约形状。修复是在
提示词末段（分隔线之上）增补「契约硬规则块」。本守卫只钉关键字段——句型枚举、
kind↔type/polarity 绑定措辞、块的位置——不钉正文全部，防止规则块被误删或改残。
"""
from memory.extraction_prompt import EXTRACTION_PROMPT

_SEPARATOR = "===== 以上为固定规则"

# 服务端句型表的每个 predicate 对应提示词里必须出现的表面句型（2026-11-25 紧凑格式：
# 模型不再填 predicate_key，只需按句型写 content，谓词由服务端推导）
_SURFACE_FORMS = {
    "profile.residence": "我住在X", "profile.origin": "我来自X", "profile.nickname": "我叫X",
    "profile.employer": "我在X工作", "profile.residence.en": "I live in X",
    "profile.origin.en": "I am from X", "profile.nickname.en": "My name is X",
    "preference.general": "我喜欢X", "identity.state": "我是X", "identity.have": "我有X",
    "identity.state.en": "I am X", "identity.have.en": "I have X", "plan.intend": "我打算X",
    "plan.want": "我想X", "plan.will": "我要X", "plan.doing": "我正在X",
    "plan.going_to.en": "I'm going to X", "plan.want_to.en": "I want to X",
    "ability.can": "我会X", "ability.can.en": "I can X", "ability.play.en": "I play X",
    "past.used_to": "我以前/曾经X", "past.used_to.en": "I used to X",
    "past.went_to.en": "I went to X", "past.had.en": "I had X",
}


def test_every_server_pattern_has_a_surface_form_in_the_prompt():
    from memory import evidence_contract as ec
    known = {"preference.general"}
    for family in (ec._SELF_REPORT_PATTERNS, ec._IDENTITY_STATE_PATTERNS, ec._PLAN_INTENT_PATTERNS,
                   ec._ABILITY_HABIT_PATTERNS, ec._PAST_EVENT_PATTERNS):
        known |= set(family)
    assert known == set(_SURFACE_FORMS), "闸门句型扩缩时须同步提示词与本表"
    for predicate, form in _SURFACE_FORMS.items():
        assert form in EXTRACTION_PROMPT, f"提示词丢失 {predicate} 的句型「{form}」"


def test_prompt_uses_compact_fields_and_kind_bindings():
    """合同字段由服务端推导：模型只填 statement_kind，绑定措辞与 other 否决必须在。"""
    for kind in ("self_report", "explicit_preference", "identity_state", "plan_intent",
                 "ability_habit", "past_event"):
        assert f"- {kind}（type=" in EXTRACTION_PROMPT
    assert "一律填 other" in EXTRACTION_PROMPT
    for binding in ("self_report（type=FACT", "explicit_preference（type=PREFERENCE", "plan_intent（type=PLAN"):
        assert binding in EXTRACTION_PROMPT
    for dropped in ('"verification_contract":', '"canonical_value":', '"evidence":', "exact_support_span"):
        assert dropped not in EXTRACTION_PROMPT


def test_contract_block_sits_above_separator_with_messages_last():
    """硬规则块属于固定指令：在分隔线之上，且 {messages} 仍是最后的数据占位符。"""
    sep = EXTRACTION_PROMPT.index(_SEPARATOR)
    assert EXTRACTION_PROMPT.index("我住在X") < sep
    assert EXTRACTION_PROMPT.rindex("{messages}") > sep


def test_contract_block_forbids_translating_source_language():
    """2026-11-21 写侧诊断：模型把英文源句译成中文句型，必被 content_not_exact_support 拒绝。"""
    sep = EXTRACTION_PROMPT.index(_SEPARATOR)
    rule = EXTRACTION_PROMPT.index("保持原文语言")
    assert rule < sep
    assert "不要把原文翻译" in EXTRACTION_PROMPT
