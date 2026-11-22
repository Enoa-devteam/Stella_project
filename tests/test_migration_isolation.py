# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，详见项目根目录 LICENSE。
"""迁移只能写它被要求迁移的那个库，绝不能碰运行时的 ``DB_PATH``。

v6.4.0 发布前发现：v24 的预算表 DDL 另开连接写全局 ``DB_PATH``。预演因此在目标
数据根里造出一个空库，随后真正导入时以「已存在」跳过用户的记忆库，还报告成功。
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from deploy import migrate
from mneme import schema
from mneme.migrations import MigrationContext

BUDGET_TABLES = {"aoede_proactive_budget", "aoede_budget_reservations"}


def _v22_db(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript(
            "CREATE TABLE schema_meta ("
            "k TEXT PRIMARY KEY, version INTEGER, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);"
            "INSERT INTO schema_meta (k, version) VALUES ('version', 22);"
            "CREATE TABLE group_messages (id INTEGER PRIMARY KEY, group_id TEXT, content TEXT);"
            "INSERT INTO group_messages VALUES (1, '77', 'KEEP-ME');"
        )
    return path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tables(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _ctx() -> MigrationContext:
    return MigrationContext(resolver=lambda group_id: str(group_id))


def test_dry_run_leaves_live_database_untouched(tmp_path, monkeypatch):
    live = _v22_db(tmp_path / "home" / "memory" / "agent_memory.db")
    monkeypatch.setattr(schema, "DB_PATH", live)
    before = _digest(live)

    assert schema.migrate_to_latest(live, ctx=_ctx(), dry_run=True).ok

    assert _digest(live) == before


def test_migrating_a_copy_never_writes_live_database(tmp_path, monkeypatch):
    live = _v22_db(tmp_path / "home" / "memory" / "agent_memory.db")
    copy = _v22_db(tmp_path / "rehearsal" / "copy.db")
    monkeypatch.setattr(schema, "DB_PATH", live)
    before = _digest(live)

    assert schema.migrate_to_latest(copy, ctx=_ctx()).ok

    assert _digest(live) == before
    assert _tables(copy) >= BUDGET_TABLES, "v24 的表必须建在被迁移的库里"


def test_in_place_upgrade_creates_budget_tables(tmp_path, monkeypatch):
    live = _v22_db(tmp_path / "home" / "memory" / "agent_memory.db")
    monkeypatch.setattr(schema, "DB_PATH", live)

    assert schema.migrate_to_latest(live, ctx=_ctx()).ok

    assert _tables(live) >= BUDGET_TABLES


@pytest.mark.parametrize("memory_dir_exists", [False, True])
def test_dry_run_then_import_keeps_user_rows(tmp_path, monkeypatch, memory_dir_exists):
    old = tmp_path / "old"
    new = tmp_path / "new"
    source = _v22_db(old / "memory" / "agent_memory.db")
    for root in (old, new):
        root.mkdir(exist_ok=True)
        (root / "bot.py").write_text("# entry\n", encoding="utf-8")
        (root / "pyproject.toml").write_text('version = "1.0.0"\n', encoding="utf-8")
        (root / ".env").write_text("ALLOWED_GROUPS=77\n", encoding="utf-8")
    target = new / "memory" / "agent_memory.db"
    if memory_dir_exists:
        target.parent.mkdir()
    monkeypatch.setattr(schema, "DB_PATH", target)
    before = _digest(source)

    migrate.run(new, old, dry_run=True)
    assert not target.exists(), "预演不得创建目标库"

    migrate.run(new, old)
    with closing(sqlite3.connect(target)) as conn:
        assert conn.execute("SELECT content FROM group_messages").fetchall() == [("KEEP-ME",)]
    assert _digest(source) == before, "旧目录只读"
