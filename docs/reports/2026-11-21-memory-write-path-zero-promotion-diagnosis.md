# 生产写侧 0 晋升根因诊断（PR #130，2026-11-21）

- 状态：**调查完成，未修改生产代码。** 结论只覆盖 MemUse M6 5-pair 隔离样本与离线句型覆盖统计；修复、回归与真实 QQ/WebChat 验收均 NOT RUN。
- 背景：B04（10 场景 828 候选）与 B05 M6（5-pair 48 候选、full72 partial）在生产等价写侧均为全部 `OBSERVING`、`memories` 0 行。见 [B04 报告](2026-11-04-proactive-memory-benchmark-b04.md)、[B05 报告](2026-11-11-proactive-memory-benchmark-b05.md)。
- 运行：本地 8081 不可用，使用用户临时授权的 DeepSeek 公共 API `deepseek-flash` 作 MEMORY/reply/judge 模型，属诊断替身，非生产等价模型。三轮均为 `--tasks m6 --channel rule --m6-pairs 5`、最短历史 5 pairs、隔离 workdir（Git Bash `/tmp` = `%TEMP%`）；报告均 `MEASURED_IN_SCOPE` / `COMPLETE`、0 errors。API key 未落盘（grep 验证）。

## 晋升门的实际条件

`MemoryManager._decide_promotion`（`mneme/memory_manager.py`）在看置信度前先要求 `verification_status == "accepted"`。accepted 只来自 `mneme/evidence_contract.py:assess_candidate`，需要候选同时满足：附带 `verification_contract`；`content` 逐字等于每个 `exact_support_span` 且是源消息子串；作者即事实主体；span 不含条件/引号/疑问，并 fullmatch（或扩展族 search）某个固定句型且值段等于 `canonical_value`。

只有阶段 2（`mneme/extraction_prompt.py`，角色 EXTRACT）要求输出该合同。阶段 1（`mneme/consolidation_prompt.py`）产出改写式候选、不带合同；阶段 2 调用失败、截断或被预算拦下时，`Consolidator._extract_candidates` 返回 None 并**回退阶段 1 候选**写库。

## 三轮诊断运行

| 运行 | MEMORY 配置 | calls | 结果 | 报告 SHA-256 |
| --- | --- | ---: | --- | --- |
| `m6-dsflash-5pairs` | `kind=online`（不发 `reasoning_effort=none`，模型默认 high 推理），生产上限 1200/1000 | 43 | consolidation 全部 `finish_reason=length` 且 content 为空 → 整合失败，**0 候选** | `e6b550cc6186d8392e72e704f69d2444dd95400cdcd6c135510b4d4c6895a291` |
| `m6-dsflash-5pairs-cap8k` | `kind=online`，上限放宽到 8000/4000（仅诊断） | 49 | consolidation 截断 3、阶段 2 三次尝试均在 4000 截断 → 回退阶段 1；6 候选全 OBSERVING，8 条 evidence 全 `unknown: contract_missing` | `3f294716c74b0e8871e73559706271c8482889616b76b60712590c4c569b2123` |
| `m6-dsflash-5pairs-local` | `kind=local`（发 `reasoning_effort=none`），**生产上限 1200/1000** | 53 | 58 候选全 OBSERVING、0 active；阶段 2 调用 9 次、**8 次在 1000 截断**并回退；76 条 evidence：72 `unknown: contract_missing`、4 `rejected: content_not_exact_support` | `48808504424896480fa098cb79fe5a3ff719dcd68bcfaab4b305de82c4f3ceb7` |

第三轮 56/58 候选 confidence ≥ 0.85，若 evidence accepted 即会按「高置信直接晋升」通过；阻断点完全在 evidence 层。4 条 rejected 来自唯一未截断的阶段 2 输出：模型把英文源句翻译成提示词里的中文句型（如 "My name is Rosie" → 「我叫Rosie」、"I like warm weather" → 「我喜欢温暖的天气」），因此 content 不再是源消息逐字子串。

## 根因（按影响排序）

1. **阶段 2 截断 → 回退到结构上不可晋升的阶段 1 候选（主因）。** 生产 EXTRACT 上限 1000 token 在无推理模式下仍 8/9 截断（B04 qwen 99%）。回退候选不带合同，`assess_candidate` 必然 `contract_missing`，只能停在 OBSERVING 直到 TTL 被拒。回退路径因此不是「降级」，而是静默的 0 晋升；本次 76 条 evidence 中 72 条属此类。
2. **阶段 2 成功时的语言/逐字冲突。** 提示词为中文、示例为中文句型，模型对英文源消息输出中文翻译，违反逐字要求（4/4 rejected）。生产 QQ 用户以中文为主，此项部分属 MemUse 英文数据的评测伪影，但说明逐字合同对模型改写零容忍。
3. **潜在缺陷：ASCII 撇号被当作引号。** `_QUOTE_MARKS` 含 `'`，任何含撇号的 span 都记 `conditional_quoted_or_roleplay`。提示词明确列出的 `I'm from X`、`I don't like X`、`I'm going to X` 与 `plan.going_to.en` 正则本身因此永远无法 accepted。离线统计（零模型调用）：MemUse 144 项 21,770 条用户发言 / 57,175 句中，3,064 条发言含至少一个命中句型的句子；命中句中 807 句仅因词内撇号（所有格/缩写）被阻断，另 665 句含其他引号字符（未细分，可能含弯撇号 `’`）。tests 中无覆盖撇号的用例。
4. **配置隐患：在线推理端点吃满输出上限。** `kind=online` 不发 `reasoning_effort=none`；对默认推理的在线模型，1200 甚至 8000 token 都被推理消耗，content 为空。

## 未运行与限制

- 每轮仅 5 pairs，模型为 DeepSeek 替身；qwen 生产引擎上的阶段 2 截断率引用 B04 结果，未在本轮复测。
- 撇号统计是句型上限估计，不等于模型实际会输出的合同；修复后的晋升率需重跑 M6 验证。
- 未修改 `mneme/`、提示词或配置；修复须按计划另开产品包，先保存本报告作为失败基线，并在编辑前做 GitNexus upstream impact（`assess_candidate`、`_extract_candidates`、`_decide_promotion` 位于晋升关键路径）。
- 本诊断使用 145 次模型调用；本会话 DeepSeek 累计 2,261 / 3,000。
