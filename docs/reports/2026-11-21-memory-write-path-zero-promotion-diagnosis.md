# 生产写侧 0 晋升根因诊断（PR #130，2026-11-21）

- 状态：**诊断完成；已做最小修复并复测（见文末「修复与复测」）。** 修复后 M6 首次出现 active memory（5-pair 5 个、15-pair partial 8 个），但晋升率仍低、样本为 DeepSeek 替身，不构成写后检索验收；qwen 生产引擎复测与真实 QQ/WebChat 验收 NOT RUN。
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

## 未运行与限制（诊断阶段）

- 每轮仅 5 pairs，模型为 DeepSeek 替身；qwen 生产引擎上的阶段 2 截断率引用 B04 结果，未在本轮复测。
- 撇号统计是句型上限估计，不等于模型实际会输出的合同；修复后的晋升率需重跑 M6 验证。
- 未修改 `mneme/`、提示词或配置；修复须按计划另开产品包，先保存本报告作为失败基线，并在编辑前做 GitNexus upstream impact（`assess_candidate`、`_extract_candidates`、`_decide_promotion` 位于晋升关键路径）。
- 本诊断使用 145 次模型调用；本会话 DeepSeek 累计 2,261 / 3,000。

## 修复与复测（2026-11-21）

修复只覆盖上面第 1–3 项，不改晋升门阈值、TTL、默认 token 上限或阶段 1 回退语义：

| 修复 | 位置 | 行为 |
| --- | --- | --- |
| 阶段 2 截断拆分重试 | `mneme/consolidator.py` `_extract_candidates` → 新 `_extract_chunk` | `finish_reason=length` 时按行对半拆分、两半不重叠，最多 2 层（单批 ≤7 次调用）；每次拆分前重查 EXTRACT 日预算；任一半失败或拆到底仍截断才返回 None 走原回退。 |
| 词内撇号 | `mneme/evidence_contract.py` `assess_candidate` | 两侧均为字母的 `'` / `’` 不参与引号判定；句首/句尾/空格旁的引号仍阻断。 |
| 保持原文语言 | `mneme/extraction_prompt.py` 合同硬规则块（缓存分隔符之前） | 明确禁止把原文翻译后填 content / exact_support_span。 |

编辑前 GitNexus upstream impact：`_extract_candidates` **CRITICAL**（31 direct / 7 processes / 13 modules / 300 impacted；depth-1 多为同名 METHOD_OVERRIDES 解析噪声，未作豁免）；`assess_candidate` 与 `format_extraction_prompt` 为 UNKNOWN，文本搜索确认生产调用点仅 `mneme/consolidator.py`（927 行阶段 2；1596/1634 行候选写入）与 `scripts/probe_consolidation.py`。

### 验证

- 新增/扩展测试：`tests/test_extract_truncation_split.py`（拆分合并、拆到底回退、单行不拆、拆分时预算拦截）、`tests/test_memory_evidence_contract.py`（4 个词内撇号用例 + 3 个真实引号守卫）、`tests/test_extraction_prompt_contract.py`（语言规则位于缓存分隔符前）。撇号用例在修复前代码上 4 failed、修复后通过；相关套件 70 passed。
- 全量 `python -m pytest tests -q --continue-on-collection-errors`（本机 miniconda Python 3.14）：4,386 passed / 22 skipped / 11 failed / 1 collection error。其中 message-flow drift gate 由本改动引起，已用 `python scripts/generate_message_flow.py` 重新生成 `core/observability/flows/message-flow.d08ef6688b3f.json`，`--check` ok、该测试文件 15 passed。其余 10 failed 在 HEAD（改动 stash 后）同样失败（corona/nucleus/gravitas/config_revision 托管进程与 nonebot driver 相关），collection error 为本机缺 `nonebot.adapters.qq`；均为既有环境问题，与本改动无关。`ruff check .` PASS。
- 提交前 `detect-changes --scope all`：9 files / 9 symbols / 781 affected processes / **CRITICAL**。列出的流程多经 `_extract_candidates` 宽泛归因（如 `Get_config → Sha256_hex`），但按规则不豁免；实际行为变化限于阶段 2 提取与证据审核，由上述测试与 M6 复测覆盖。

### M6 复测（DeepSeek 替身，`kind=local`、生产上限 1200/1000）

| 运行 | 范围 | calls | 结果 | 报告 SHA-256 |
| --- | --- | ---: | --- | --- |
| 修复前 `m6-dsflash-5pairs-local` | 5 pairs | 53 | 58 候选全 OBSERVING、0 active；positive integration 1/5、packed 0/5 | `48808504424896480fa098cb79fe5a3ff719dcd68bcfaab4b305de82c4f3ceb7` |
| 修复后 `m6-dsflash-5pairs-local-fixed` | 同 5 pairs | 85 | `COMPLETE`、0 errors；66 候选中 **5 CONFIRMED / 5 active memories**；positive integration 2/5、packed 2/5；negative overuse 1/5、packed 1/5。阶段 2 调用 34 次，拆分 16 次，最终回退 4 次；evidence：accepted 5、contract_missing 35、semantic_contract_not_bound 18、content_not_exact_support 6 | `61f6faf82f15f68f4d42d742f289fb06b4962d15442ca913691f438c77d335d8` |
| 修复后 `m6-dsflash-15pairs-local-fixed` | 15 pairs | 450（到上限） | `PARTIAL_BUDGET`，28/30 行（15 正、13 负），唯一 error 为 BudgetExceededError；DB 计数 363 候选中 **8 CONFIRMED / 8 active**（7 个 item）；positive integration 5/15、packed 5/15；negative overuse 7/13、packed 2/13、fabricated recall 4/13。阶段 2 调用 222 次（截断 140），拆分 106 次、最终回退 35 次；evidence：accepted 12、contract_missing 272、semantic_contract_not_bound 50、canonical_value_not_supported 39、content_not_exact_support 38 | `26431bf4fe6a4d523821455a0f87647e23570d6823905dc205d9a9b87b598dfc` |

结论（仅限本范围）：修复首次让生产等价写侧产出 active memory 并在 M6 回复中被检索使用；但晋升率仍低（15-pair 2.2%），不构成「写后检索有效」的验收。15-pair 为 partial，无 M6−M0 配对估计；样本小、模型为替身、reply/judge 同模型。

### 修复后的新成本与剩余阻断

- 拆分重试把阶段 2 调用放大（15-pair：222 次 extract 对 135 次 consolidation）。1000 token 的 EXTRACT 上限对带合同的输出仍偏小；是否调整默认上限或压缩输出格式需单独决定（会影响用户的本地推理占用与日预算）。
- `contract_missing` 仍为最大类：拆到底仍截断的批次、以及阶段 1 未标 `has_self_disclosure` 而不触发阶段 2 的批次，都会写入无合同候选。
- 阶段 2 成功后的主要拒绝原因转为 `semantic_contract_not_bound_to_supported_form`、`canonical_value_not_supported` 与翻译导致的 `content_not_exact_support`：句型覆盖窄与模型合同填写精度问题，需要扩展句型或调整提示（另包）。
- 本会话 DeepSeek 累计 2,796 / 3,000 calls；qwen 生产引擎复测、M6 full72、真实 QQ/WebChat 未运行。
