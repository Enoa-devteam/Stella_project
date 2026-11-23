# P1 证据合同扩展生产化（独立 PR：`codex/evidence-contract-expansion`）

> 归档：原为本地会话计划 `.zcode/plans/plan-session_336c42cadee7b4396161f4d29c54c8fa.md`（2026-11-02），2026-11-23 移入 `docs/plans/`；正文未改，仅为计划，不作为实施或验收证明。

## Context

PR #127 已合并（本分支基于更新后的 origin/main 新建）。MBENCH-004 P1 离线对照已完成（A0 2.1% → A1 扩句型 21.0% 召回 / A2 语义过滤精度代理 97.2%，202 样本标注集），按计划组织方式现在落地生产：扩展 `memory/evidence_contract.py` 的验收句型族并同步提取提示词，**使写侧从「自然语言几乎无法形成记忆」（live 漏斗 188 候选 0 晋升）走向可用**。验收标准（计划 §P1）：MUST_CAPTURE 召回 ≥21%、MUST_NOT 零错误晋升、硬门禁零失败、同一批候选可归因。

## 设计决策（探索后定稿）

1. **精确镜像已验证的 A1+A2**：只上线离线对照验证过的句型族与过滤器，不额外发挥。句型族（来自 contract_study A1，与 gold 202 的 21%/97.2% 数字一一对应）。
2. **新 statement_kind 分类 + type 绑定**（沿用 kind↔type 绑定机制 evidence_contract.py:493-499）：
   - `self_report`（既有 7 谓词不动）→ FACT
   - `explicit_preference`（既有）→ PREFERENCE
   - `identity_state`（新：identity.am/have + en_am/en_have）→ FACT
   - `plan_intent`（新：plan.intend/want/will/doing + en_gonna/en_want）→ **PLAN**（自动获得 14 天 TTL——P1-3 要求的计划时效管理）
   - `ability_habit`（新：ability.can/en_can/en_play）→ FACT
   - `past_event`（新：past.used_to/en_used/en_went/en_had）→ FACT
   - 全部新族 polarity=positive only（保守起点）
3. **A2 语义过滤进 assess_candidate 语义段**（全 kind 生效）：值段第二人称宾语（拒绝夸赞误归因）、占位符 `X`、值段 <2 字符；既有 conditional/quoted/question 过滤不动。新增拒绝 reason：`value_second_person` / `value_placeholder` / `value_too_short`。
4. **不 bump ASSESSMENT_VERSION**（关键范围决策）：避免 Rust 常量级联 + .pyd 重编译；归因改用 predicate_key（claim_key 哈希含 predicate_key，新族谓词即家族标记；provenance 可按谓词审计）。诚实记录：版本级归因推迟到结构化候选重设计。
5. **主体归一化不做**（32 例漏检的最高杠杆但需名字解析，探索确认生产无可靠映射）；提示词改为教模型「第一人称陈述取逐字原文」，覆盖大部分三人称形态。

## 改动文件

1. `memory/evidence_contract.py`：`_ACCEPTED_KINDS` 扩 4；新谓词模式表（沿用 `_SELF_REPORT_PATTERNS` 同构风格）；`_semantic_contract_matches` 扩新 kind 分支（fullmatch+value 等同+positive）；A2 三过滤器进 `assess_candidate` 语义段（新 reason 常量）；kind↔type 绑定表扩 4 条。
2. `memory/extraction_prompt.py`：契约硬规则块同步扩枚举（新句型族逐字规则 + 「第一人称陈述取逐字原文」指引 + 新反例），保持 `{messages}` 在末位与分隔符结构。
3. `tests/test_extraction_prompt_contract.py`：`_AUDITABLE_PREDICATE_KEYS` 扩新谓词；绑定短语断言扩新 kind。
4. `tests/test_memory_evidence_contract.py`：每新族正例（accepted + 谓词/主体绑定）+ 反例（第二人称宾语值「我喜欢你画画」、占位符、短值、否定身份）。
5. `memory_eval/contract_study.py`：加 `--shipped` 配置 = 直接调用生产 `assess_candidate` 语义段（消双实现漂移），对 gold 202 复算并归档。
6. 文档：`docs/architecture/memory-system.md`（.en）句型族清单更新；报告 `docs/reports/2026-11-02-contract-expansion-production.md`（.en）含误晋升审计（MUST_NOT=0 晋升、MAY 验收数、精度代理）。
7. 登记：feature `MEMWRT-001`（证据合同扩展生产化）+ progress.md + session-handoff.md。

## 不在本 PR

- 主体归一化、结构化候选+span 绑定全重设计（P1-3 远期路径）；ASSESSMENT_VERSION bump（随结构化重设计）；提取模型行为变化验证（需 live 重跑，标注 NOT READY）；P4-3 真实写侧端到端。

## 验证

1. GitNexus impact `assess_candidate`（编辑前）；UNKNOWN 则源码清点（consolidator.py:1595/1633 唯一调用，已有）。
2. 定向 pytest：test_memory_evidence_contract / test_extraction_prompt_contract / test_memory_eval* / test_memory_reliability_flags / 硬门禁三套件（cross_user_isolation / personal_memory_sharing / private_chat_ingress）+ test_candidate_reinforcement（unknown 不晋升）。
3. `python -m memory_eval.contract_study --shipped`：对 gold 202 出生产验收数字（MUST ≥21%、MUST_NOT ≤1、精度代理 ≥94.6%），结果入 evidence。
4. `ruff check .` / `check_docs.py` / `detect-changes --scope all`。
5. 提交推送至新分支 `codex/evidence-contract-expansion`，开新 PR（base main），PR 描述含对照表与误晋升审计。