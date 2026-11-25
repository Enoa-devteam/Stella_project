# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 Stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，详见项目根目录 LICENSE。
"""Regression tests for server-owned memory evidence binding."""

import sqlite3

import pytest

from core.transport.keys import conversation_key_v2
from core.transport.models import BotRef, SceneRef, UserRef
from memory.evidence_contract import (
    assess_candidate,
    source_digest,
    verify_source_snapshot,
)
from memory.ownership import person_owner_key_for_subject


def _database(tmp_path, *, source_kind="AT_MENTION", author="111", bot_id="bot-a"):
    conn = sqlite3.connect(tmp_path / "evidence.db")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE group_messages ("
        "id INTEGER PRIMARY KEY, group_id TEXT, user_id TEXT, content TEXT, "
        "source_kind TEXT, timestamp TEXT, conversation_key TEXT, bot_id TEXT)"
    )
    conn.execute(
        "INSERT INTO group_messages VALUES (1, '1001', ?, ?, ?, '2026-10-09T00:00:00', ?, ?)" ,
        (author, "我住在上海", source_kind, "qq:bot-a:group:1001", bot_id),
    )
    conn.commit()
    return conn


def _candidate(
    *,
    content="我住在上海",
    value="上海",
    predicate="profile.residence",
    polarity="positive",
    statement_kind="self_report",
    user_id="111",
    source_ids=None,
):
    kind_types = {
        "explicit_preference": "PREFERENCE",
        "plan_intent": "PLAN",
    }
    return {
        "user_id": user_id,
        "type": kind_types.get(statement_kind, "FACT"),
        "content": content,
        "source_message_ids": source_ids or [1],
        "owner_key": "space:1001",
        "audience": "CURRENT_SPACE",
        "verification_contract": {
            "fact_subject_user_id": user_id,
            "predicate_key": predicate,
            "canonical_value": value,
            "polarity": polarity,
            "statement_kind": statement_kind,
            "temporal_qualifiers": [],
            "context_qualifiers": [],
            "supports": [{"source_message_id": 1, "exact_support_span": content}],
        },
    }


def _assess(conn, candidate, *, allowed=(1,), conversation="qq:bot-a:group:1001", bot="bot-a"):
    return assess_candidate(
        conn,
        candidate,
        group_id=1001,
        allowed_batch_ids=set(allowed),
        expected_conversation_key=conversation,
        expected_bot_id=bot,
    )


def test_exact_self_report_binds_subject_predicate_value_and_source(tmp_path):
    conn = _database(tmp_path)
    result = _assess(conn, _candidate())
    conn.close()

    assert result["status"] == "accepted"
    assert result["fact_subject_key"] == "qq:111"
    assert result["sources"][0]["verification_status"] == "accepted"
    snapshot = result["sources"][0]["snapshot"]
    digest = result["sources"][0]["source_digest"]
    assert source_digest(snapshot) == digest
    assert verify_source_snapshot(snapshot, digest)
    assert not verify_source_snapshot({**snapshot, "content": "改过的来源"}, digest)


def test_explicit_negative_preference_is_bound_to_negative_value(tmp_path):
    conn = _database(tmp_path)
    conn.execute("UPDATE group_messages SET content = '我不喜欢香菜' WHERE id = 1")
    candidate = _candidate(
        content="我不喜欢香菜",
        value="香菜",
        predicate="preference.general",
        polarity="negative",
        statement_kind="explicit_preference",
    )
    result = _assess(conn, candidate)
    conn.close()
    assert result["status"] == "accepted"


@pytest.mark.parametrize(
    ("content", "predicate", "value", "polarity", "statement_kind"),
    [
        ("如果我住在上海", "profile.residence", "上海", "positive", "self_report"),
        ("他说‘我住在上海’", "profile.residence", "上海", "positive", "self_report"),
        ("我住在上海吗？", "profile.residence", "上海", "positive", "self_report"),
        ("我住在上海", "profile.favorite_color", "上海", "positive", "self_report"),
        ("我不喜欢香菜", "preference.general", "香菜", "positive", "explicit_preference"),
    ],
)
def test_ambiguous_or_mismatched_semantics_never_accept(
    tmp_path, content, predicate, value, polarity, statement_kind
):
    conn = _database(tmp_path)
    if content != "我住在上海":
        conn.execute("UPDATE group_messages SET content = ? WHERE id = 1", (content,))
    candidate = _candidate(
        content=content,
        value=value,
        predicate=predicate,
        polarity=polarity,
        statement_kind=statement_kind,
    )
    result = _assess(conn, candidate)
    conn.close()
    assert result["status"] != "accepted"


def test_wrong_author_and_bot_speech_cannot_be_personal_evidence(tmp_path):
    conn = _database(tmp_path, author="222")
    assert _assess(conn, _candidate())["status"] == "unknown"
    conn.execute("UPDATE group_messages SET source_kind = 'BOT_SELF', user_id = '111' WHERE id = 1")
    assert _assess(conn, _candidate())["status"] == "rejected"
    conn.close()


def test_unknown_source_kind_and_missing_bot_binding_fail_closed(tmp_path):
    conn = _database(tmp_path, source_kind="UNREGISTERED")
    assert _assess(conn, _candidate())["status"] == "unknown"
    conn.execute("UPDATE group_messages SET source_kind = 'AT_MENTION', bot_id = '' WHERE id = 1")
    assert _assess(conn, _candidate())["status"] == "unknown"
    conn.close()


def test_source_must_be_in_exact_batch_and_current_conversation(tmp_path):
    conn = _database(tmp_path)
    assert _assess(conn, _candidate(), allowed=())["status"] == "rejected"
    assert _assess(conn, _candidate(), conversation="qq:other:group:1001")["status"] == "rejected"
    conn.close()


def test_v2_source_uses_namespaced_subject_and_connection_owner(tmp_path):
    conn = _database(tmp_path)
    conn.execute("ALTER TABLE group_messages ADD COLUMN subject_key TEXT NOT NULL DEFAULT ''")
    conn.execute("ALTER TABLE group_messages ADD COLUMN connection_id TEXT NOT NULL DEFAULT ''")
    user = UserRef("service:alpha", "111")
    bot = BotRef("connection-a", "generic", "service", "bot-a")
    conversation = conversation_key_v2(bot, SceneRef("group", "1001"))
    conn.execute(
        "UPDATE group_messages SET subject_key=?, connection_id=?, conversation_key=? WHERE id=1",
        (user.subject_key, bot.connection_id, conversation),
    )
    conn.commit()

    result_a = assess_candidate(
        conn,
        _candidate(),
        group_id=1001,
        allowed_batch_ids={1},
        expected_conversation_key=conversation,
        expected_bot_id="bot-a",
    )
    assert result_a["status"] == "accepted"
    assert result_a["fact_subject_key"] == user.subject_key
    assert result_a["owner_key"] == person_owner_key_for_subject(
        "connection-a", user.subject_key
    )
    snapshot = result_a["sources"][0]["snapshot"]
    assert snapshot["connection_id"] == "connection-a"
    assert verify_source_snapshot(
        snapshot, result_a["sources"][0]["source_digest"], conn=conn
    )

    user_b = UserRef("service:beta", "111")
    bot_b = BotRef("connection-b", "generic", "service", "bot-a")
    conversation_b = conversation_key_v2(bot_b, SceneRef("group", "1001"))
    conn.execute(
        "UPDATE group_messages SET subject_key=?, connection_id=?, conversation_key=? WHERE id=1",
        (user_b.subject_key, bot_b.connection_id, conversation_b),
    )
    conn.commit()
    result_b = assess_candidate(
        conn,
        _candidate(),
        group_id=1001,
        allowed_batch_ids={1},
        expected_conversation_key=conversation_b,
        expected_bot_id="bot-a",
    )
    conn.close()
    assert result_b["status"] == "accepted"
    assert result_b["fact_subject_key"] == user_b.subject_key
    assert result_b["owner_key"] != result_a["owner_key"]


def test_empty_added_identity_columns_do_not_change_legacy_snapshot_hash():
    from memory.evidence_contract import _snapshot

    legacy_row = {"id": 1, "group_id": "1001", "user_id": "111", "content": "x"}
    before = _snapshot(legacy_row)
    after = _snapshot({**legacy_row, "subject_key": "", "connection_id": ""})
    assert after == before
    assert source_digest(after) == source_digest(before)


def _content_row(tmp_path, content, candidate, *, marker=""):
    sub = tmp_path / f"db-{marker or abs(hash(content))}"
    sub.mkdir(parents=True, exist_ok=True)
    conn = _database(sub)
    conn.execute("UPDATE group_messages SET content = ? WHERE id = 1", (content,))
    result = _assess(conn, candidate)
    conn.close()
    return result


def test_identity_state_family_accepted(tmp_path):
    result = _content_row(
        tmp_path, "我是单亲家长",
        _candidate(content="我是单亲家长", value="单亲家长",
                   predicate="identity.state", statement_kind="identity_state"),
    )
    assert result["status"] == "accepted"
    assert "identity.state" in result["claim_key"] or result["claim_key"].startswith("claim:v1:")


def test_plan_intent_family_accepted_with_plan_type(tmp_path):
    result = _content_row(
        tmp_path, "我打算下个月去露营",
        _candidate(content="我打算下个月去露营", value="下个月去露营",
                   predicate="plan.intend", statement_kind="plan_intent"),
    )
    assert result["status"] == "accepted"


def test_ability_and_past_families_accepted(tmp_path):
    result = _content_row(
        tmp_path, "我会拉小提琴",
        _candidate(content="我会拉小提琴", value="拉小提琴",
                   predicate="ability.can", statement_kind="ability_habit"),
        marker="ability",
    )
    assert result["status"] == "accepted"
    result = _content_row(
        tmp_path, "我以前很喜欢打篮球",
        _candidate(content="我以前很喜欢打篮球", value="很喜欢打篮球",
                   predicate="past.used_to", statement_kind="past_event"),
        marker="past",
    )
    assert result["status"] == "accepted"


def test_expanded_family_rejections(tmp_path):
    """第二人称宾语值 / 占位符 / 过短值 → 不 accepted（A2 值段过滤器）。"""
    result = _content_row(
        tmp_path, "我喜欢你画画",
        _candidate(content="我喜欢你画画", value="你画画",
                   predicate="preference.general",
                   statement_kind="explicit_preference"),
        marker="sec",
    )
    assert result["status"] != "accepted"
    assert "value_second_person" in result["reason"]

    result = _content_row(
        tmp_path, "我住在X",
        _candidate(content="我住在X", value="X",
                   predicate="identity.state", statement_kind="identity_state"),
        marker="ph",
    )
    assert result["status"] != "accepted"
    assert "value_placeholder" in result["reason"]

    result = _content_row(
        tmp_path, "我会唱",
        _candidate(content="我会唱", value="唱",
                   predicate="ability.can", statement_kind="ability_habit"),
        marker="short",
    )
    assert result["status"] != "accepted"
    assert "value_too_short" in result["reason"]


# ── 2026-11-21 写侧诊断：词内撇号不是引号 ─────────────────────────────


@pytest.mark.parametrize(
    ("content", "predicate", "value", "polarity", "statement_kind"),
    [
        ("I'm from Osaka", "profile.origin.en", "Osaka", "positive", "self_report"),
        ("I don't like cilantro", "preference.general", "cilantro", "negative", "explicit_preference"),
        ("I don’t like cilantro", "preference.general", "cilantro", "negative", "explicit_preference"),
        ("I have my daughter's old bike", "identity.have.en", "my daughter's old bike", "positive", "identity_state"),
    ],
)
def test_in_word_apostrophe_is_not_a_quote_mark(tmp_path, content, predicate, value, polarity, statement_kind):
    conn = _database(tmp_path)
    conn.execute("UPDATE group_messages SET content = ? WHERE id = 1", (content,))
    candidate = _candidate(content=content, value=value, predicate=predicate,
                           polarity=polarity, statement_kind=statement_kind)
    result = _assess(conn, candidate)
    conn.close()
    if "’" in content:
        # 弯撇号不在 _PREFERENCE_PATTERN_EN 的 don't 里，句型本身不命中；
        # 但拒绝原因只能是句型不符，不能再是「引号/角色扮演」。
        assert "conditional_quoted_or_roleplay" not in result["reason"]
    else:
        assert result["status"] == "accepted", result["reason"]


@pytest.mark.parametrize(
    "content",
    ["'I live in Osaka'", "He said 'I live in Osaka", "I live in 'Osaka'"],
)
def test_real_ascii_quotes_still_block_acceptance(tmp_path, content):
    conn = _database(tmp_path)
    conn.execute("UPDATE group_messages SET content = ? WHERE id = 1", (content,))
    candidate = _candidate(content=content, value="Osaka", predicate="profile.residence.en")
    result = _assess(conn, candidate)
    conn.close()
    assert result["status"] != "accepted"
    assert "conditional_quoted_or_roleplay" in result["reason"]


# ── span 之外的语境（2026-11-25）：模型把假设 / 引述句截成直接陈述 ──────────


def _assess_source(tmp_path, text, span, **kwargs):
    conn = _database(tmp_path)
    conn.execute("UPDATE group_messages SET content = ? WHERE id = 1", (text,))
    result = _assess(conn, _candidate(content=span, **kwargs))
    conn.close()
    return result


@pytest.mark.parametrize("text", [
    "如果我住在上海就好了",
    "要是我住在上海，就能天天见到你",
    "不是我住在上海",
    '他说"我住在上海"',
    "他说我住在上海",
    "他说：我住在上海",
    "她以为我住在上海",
    "歌词里写“我住在上海”",
])
def test_span_cut_out_of_hypothetical_or_quote_is_not_accepted(tmp_path, text):
    result = _assess_source(tmp_path, text, "我住在上海", value="上海")
    assert result["status"] == "unknown"
    assert "context_conditional_quoted_or_negated" in result["reason"]


@pytest.mark.parametrize("text", [
    "我住在上海",
    "不，我住在上海",
    "没有，我住在上海",
    "今天好冷。我住在上海",
    "如果有空就来玩。我住在上海",
    "如果我住在上海就好了。后来搬家了，我住在上海",
    "我喜欢“甜食”，我住在上海",
])
def test_direct_statement_with_nearby_context_still_accepted(tmp_path, text):
    assert _assess_source(tmp_path, text, "我住在上海", value="上海")["status"] == "accepted"


@pytest.mark.parametrize("text, span", [
    ("If I have a blog I will write about it.", "I have a blog"),
    ("He said I have a blog.", "I have a blog"),
    ('She said "I have a blog" to me.', "I have a blog"),
])
def test_english_hypothetical_or_reported_span_is_not_accepted(tmp_path, text, span):
    result = _assess_source(tmp_path, text, span, value="a blog", predicate="identity.have.en",
                            statement_kind="identity_state")
    assert result["status"] == "unknown"


@pytest.mark.parametrize("span, value, accepted", [
    ("I have been trying to stop", "been trying to stop", False),
    ("I have cleaned it twice", "cleaned it twice", False),
    ("I have to be careful", "to be careful", False),
    ("I have two kids", "two kids", True),
])
def test_perfect_tense_is_not_possession(tmp_path, span, value, accepted):
    result = _assess_source(tmp_path, span, span, value=value, predicate="identity.have.en",
                            statement_kind="identity_state")
    assert (result["status"] == "accepted") is accepted


# ── 服务端推导合同（阶段2 紧凑格式，2026-11-25）──────────────────────────────


def _compact(content, kind, type_, **over):
    c = _candidate(content=content)
    del c["verification_contract"]
    return {**c, "type": type_, "statement_kind": kind, **over}


def _assess_compact(tmp_path, text, content, kind, type_, **over):
    conn = _database(tmp_path)
    conn.execute("UPDATE group_messages SET content = ? WHERE id = 1", (text,))
    result = _assess(conn, _compact(content, kind, type_, **over))
    conn.close()
    return result


@pytest.mark.parametrize("content, kind, type_, predicate, value, polarity", [
    ("我住在上海", "self_report", "FACT", "profile.residence", "上海", "positive"),
    ("我不喜欢吃辣", "explicit_preference", "PREFERENCE", "preference.general", "吃辣", "negative"),
    ("我打算去北京", "plan_intent", "PLAN", "plan.intend", "去北京", "positive"),
    ("我会弹钢琴", "ability_habit", "FACT", "ability.can", "弹钢琴", "positive"),
    ("I went to a pottery workshop on Friday", "past_event", "FACT", "past.went_to.en",
     "a pottery workshop on Friday", "positive"),
])
def test_compact_candidate_contract_is_derived_by_server(
    tmp_path, content, kind, type_, predicate, value, polarity
):
    result = _assess_compact(tmp_path, content, content, kind, type_)
    assert result["status"] == "accepted", result["reason"]
    assert result["provenance"]["predicate_key"] == predicate
    assert result["provenance"]["canonical_value"] == value
    assert result["provenance"]["polarity"] == polarity


@pytest.mark.parametrize("text, content, kind, type_, reason", [
    # 模型语义否决
    ("我住在上海", "我住在上海", "other", "FACT", "contract_not_derivable"),
    ("我住在上海", "我住在上海", "roleplay", "FACT", "contract_not_derivable"),
    # 正则与模型 kind 不一致
    ("我会住在上海", "我会住在上海", "plan_intent", "PLAN", "contract_not_derivable"),
    ("我想我住在上海", "我想我住在上海", "plan_intent", "PLAN", "contract_not_derivable"),
    # 不支持的句型 / 值段带逗号
    ("我时不时会失眠", "我时不时会失眠", "self_report", "FACT", "contract_not_derivable"),
    ("我有猫，也有狗", "我有猫，也有狗", "identity_state", "FACT", "contract_not_derivable"),
    # 类型绑定、值段第二人称、语境守卫仍由 assess_candidate 把关
    ("我住在上海", "我住在上海", "self_report", "PREFERENCE", "self_report_type_mismatch"),
    ("我喜欢你画画", "我喜欢你画画", "explicit_preference", "PREFERENCE", "value_second_person"),
    ("如果我住在上海就好了", "我住在上海", "self_report", "FACT", "context_conditional_quoted_or_negated"),
    ("他说我住在上海", "我住在上海", "self_report", "FACT", "context_conditional_quoted_or_negated"),
    # 改写过的 content 不是原文子串
    ("我现在搬到了上海", "我住在上海", "self_report", "FACT", "support_span_not_in_source"),
])
def test_compact_candidate_not_accepted(tmp_path, text, content, kind, type_, reason):
    result = _assess_compact(tmp_path, text, content, kind, type_)
    assert result["status"] != "accepted"
    assert reason in result["reason"]


def test_compact_candidate_author_and_bot_guards_still_apply(tmp_path):
    conn = _database(tmp_path, author="222")
    assert _assess(conn, _compact("我住在上海", "self_report", "FACT"))["status"] != "accepted"
    conn.close()


def test_stage1_candidate_without_kind_stays_contract_missing(tmp_path):
    conn = _database(tmp_path)
    c = _compact("我住在上海", "self_report", "FACT")
    del c["statement_kind"]
    result = _assess(conn, c)
    conn.close()
    assert (result["status"], result["reason"]) == ("unknown", "contract_missing")


@pytest.mark.parametrize("content, kind, type_, accepted", [
    ("I like it.", "explicit_preference", "PREFERENCE", False),
    ("我喜欢这个", "explicit_preference", "PREFERENCE", False),
    ("I like it here in town", "explicit_preference", "PREFERENCE", True),
    ("我喜欢这个季节", "explicit_preference", "PREFERENCE", True),
])
def test_pronoun_only_value_is_not_a_fact(tmp_path, content, kind, type_, accepted):
    result = _assess_compact(tmp_path, content, content, kind, type_)
    assert (result["status"] == "accepted") is accepted
    if not accepted:
        assert "value_pronoun_only" in result["reason"]
