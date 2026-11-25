# issue #136 后续：记忆写侧与 B05 收尾（2026-11-25）

- 状态：写侧门禁修复、紧凑提取格式、独立 judge 入口、qwen 复测、embedding/hybrid 离线通道**已完成**；晋升率与回复效果仍不构成产品验收，**NOT READY**。改动以 PR 提交，#136 不随之关闭。
- 环境：引擎 Strata 8081，`qwen3.8-flash-next-iq2_xs`，n_ctx 16384（`/v1/models` 预检通过）；`--memory-kind local`，生产上限 1200/1000；隔离 workdir `E:/stella/runs/issue136`，未读写真实用户数据。代码冻结在 detached worktree：baseline = `53fcbb6`；snap1 = `53fcbb6` + 工作树补丁（SHA-256 `ca2c9d34b73288f85d54ffbb0411cee996e1e1972bba326cb46a1df84982454b`）。引擎在温度 0 下**不确定**（同批两次探针计数不同），单次差异不作结论。
- 晚于 snap1、未复跑 M6 的改动：代词值守卫、online 空回复报错文案；由单测覆盖。

## 结论一览

| #136 项 | 结果 |
| --- | --- |
| qwen 生产引擎复测 | 完成：5-pair（基线 / 新）与 15-pair（新），见下表 |
| EXTRACT 上限 / 输出格式 | 改为紧凑格式，上限维持 1000：cap 1000→4000 只多出候选（31→145），accepted 仍为 1 |
| 无合同候选 | 回退阶段 1 候选**仍写库**（维护者决定）；15-pair 仍有 52 条 `contract_missing` |
| 句型 / 合同精度 | 合同字段由服务端推导；**未扩句型** |
| 晋升率 | 15-pair 40/570 = 7.0%（此前 DeepSeek 15-pair partial 8/363 = 2.2%；样本、模型不同，非配对） |
| `conversation_identity._QUOTE_MARKS` | 确认缺陷并修复（`我叫O'Brien` 曾被丢弃；真引号仍拒绝），`PARSER_VERSION` 2026-11-25.1 |
| online 推理耗尽上限 | 空内容 + `finish=length` 报明确原因；`.env.example` 加提示。**未**加 reasoning 配置项（端点管线 impact CRITICAL，厂商中立为既定约束） |
| M6 full72 | 未运行：外推约 11,000 次调用 / 17 小时；维护者选 15-pair |
| ChMap 156/417 | 未改 selection 规则；接受或变更协议待维护者决定 |
| 独立 judge | runner 支持 `--judge-base-url` / `--judge-api-key`（回复 key 不会发到该端点）；**未用独立 judge 运行** |
| G5 | 未证明；本轮无 M6−M0 配对估计 |
| embedding / hybrid | 离线 rank / boundary 完成；joint / pairing / M6 的这两个通道未运行 |
| B06 / B07 / B08、QQ/WebChat、干净 VM | 仍受标注人员、平台授权、目标群与观察期阻断 |

## 门禁缺陷（本轮发现，已修）

晋升验收只检查 span 本身，模型把假设 / 引述句截成直接陈述即可 accepted。在未修改的 `53fcbb6` 上直接复现为 `accepted`：`如果我住在杭州就好了` → `我住在杭州`、`不是我住在杭州`、`他说"我住在杭州"`、`If I have a blog I will…` → `I have a blog`；另有 `I have been trying…` 按「拥有」接受。

- 修复：`_span_context_is_clean` 查含 span 的整句条件词、未闭合引号、紧邻否定与转述引导，至少一处干净即可。`identity.have.en` 排除完成时与 `have to`。`value_pronoun_only` 拒绝 `I like it` / `我喜欢这个`。
- 新增用例里 14 项在未修改的 `53fcbb6` 上失败、在本树通过（代词用例未计入）；「不，我住在上海」这类更正仍通过。
- **历史已 accepted 的行未回查**（不触碰用户数据）；`ASSESSMENT_VERSION` 未 bump，沿用既有做法（避免 Rust 常量级联）。

## 紧凑格式

模型只输出逐字 `content`、单个 `source_message_ids`、`statement_kind`（不确定填 `other`）等；`derive_contract` 从 span 唯一推导谓词、值、极性，且要求与模型声明的 kind 一致。同 29 批、cap 1000 的探针：旧格式 accepted 1，新格式 9 行（6 条去重，逐条看过，均为逐字第一人称陈述），截断 5/29。旧格式 cap 4000 下 verification_contract 约占候选字段字符 72%。

## M6 qwen（rule 通道）

| 运行 | 调用 / 秒 | 阶段 2 截断 | 候选 → active | 正例 integration | 负例 overuse | 报告 SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 基线 5-pair | 99 / 558 | 29/41 | 60 → 1 | 0/5 | 1/5 | `8cc5b8c7057c40ed46899fead34378c5541a828f112ea6dd87509a8375972e4c` |
| 新 5-pair | 76 / 369 | 7/23 | 88 → 3 | 0/5 | 2/5 | `a7f42147367e80053ad9394132bab3c54e3562ea34d16d4f55d1aa7516f18b8b` |
| 新 15-pair | 464 / 2592 | 86/219 | 570 → 40 | 1/15 | 6/15 | `bb44a4a2eb7c71f28ae090850b774dfa867eb79b86311980fda60b4627e4863f` |

- 三次均 `COMPLETE`、0 errors。15-pair fabricated：负例 5/15、正例 1/15；packed 正例 10/15、负例 7/15。无 M0 对照，不能判断 overuse 是否由记忆引起。
- 晋升内容多为琐事；15-pair 的 40 条中 2 条为 `I like it.`，代词守卫在其后加入、未复跑。**正例收益未显示（1/15）**：写侧产出不等于检索有效。
- B05 fingerprint 现包含写侧代码（consolidator、整合 / 提取 prompt、evidence_contract、memory_manager），避免跨版本续跑。

## Embedding / hybrid（离线，0 chat 调用）

LM Studio `text-embedding-qwen3-embedding-0.6b`，1,446 次 embedding、0 失败；报告 SHA-256 `b318936c8fc41c5e97f0fde1c650041bf6de61f7a35a59fbc90201ecade82d8c`。rule / FTS 复现既有 MRR 0.1230 / 0.1301。

| 通道 | ChMap MRR（113 可评分） | Recall@1 / @5 / @10 | MemUse gold packed（72） | 违规 |
| --- | ---: | --- | ---: | ---: |
| rule | 0.1230 | 0.035 / 0.133 / 0.319 | 72 | 0 |
| fts | 0.1301 | 0.035 / 0.133 / 0.319 | 72 | 0 |
| embedding | 0.2609 | 0.133 / 0.434 / 0.628 | 70 | 0 |
| hybrid | 0.2786 | 0.142 / 0.416 / 0.717 | 70 | 0 |

组件级检索基线，不代表回复质量；解读排名须一并看报告里的释放顺序泄漏指标（R@1 0.248）与均匀随机对照（MRR 0.137）。

## 验证

- Python 全量（Windows，3.12，uv 依赖）：4,496 passed / 30 skipped / 3 failed。3 项失败（`test_g09_policy_transport`、`test_managed_process`、`test_adapter_matrix` onebot）在同一环境的 pinned `53fcbb6` 上同样失败。`ruff check .` PASS；`check_docs.py` 0 errors。
- 提取提示词必需探针（`scripts/probe_consolidation.py --positive --two-stage --repeat 3`，qwen 8081，隔离 home）：5 个用例在 `53fcbb6` 与本树均 3/3 全命中，`insomnia_breakfast_noisy` 2/2。失眠/馒头两例与提示词示例相同，只能说明无退化，不是独立证据。真实窗口编造率探针（`--limit 20`）需用户聊天数据，未运行。
- message-flow manifest 重新生成为 `message-flow.d6fc0df790e2.json`，`--check` ok。
- GitNexus：MCP 断连，改用 CLI，索引已刷新并与 HEAD 一致。编辑前 impact：`assess_candidate` HIGH、`format_extraction_prompt` LOW、`EXTRACTION_PROMPT` UNKNOWN（文本搜索补证）、`parse_self_claim_structured` LOW、`_generate_detailed` LOW。`detect-changes --scope all`：15 files / 53 symbols / 513 流程 / **CRITICAL**（多经 `_generate_detailed` 归因），CLI 列表被截断且 `--limit` 不能补齐，**不作干净检查、未豁免**。
- 未运行：full72、独立 judge、joint / pairing 的 embedding、Linux CI、真实 QQ/WebChat、干净 VM、B06–B08。
