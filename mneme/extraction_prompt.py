# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 Stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，详见项目根目录 LICENSE。
"""记忆候选提取（两阶段整合的第二阶段）Prompt 模板。


与 consolidation_prompt.py 的分工：
- consolidation_prompt：阶段1，E4B，出 short_term + user_profiles + has_self_disclosure；
- 本模板：阶段2，27B，只做一件事——精确提取 memory_candidates。


为什么单独拆：E4B（4B）能总结主题，却系统性把候选提取判空
（log_2026_8_16_1717：7 批全空，明确「读到信息但主动弃掉」）。
候选提取是高精度抽取任务，需要 27B。


与整合 prompt 的语气差异（关键）：
本模板只在「阶段1 已判定这批含用户自我披露」时才被调用，因此基调是
「请把这些信息找出来并正确归类」，而非「没有就返回空」。空输出话术被
大幅削弱——把「是否值得记」的判断交给下游晋升闸门（Gate 1 三档 + 交叉
验证 + 配额），本步只负责「不漏」。但防编造/防张冠李戴的红线保持不变。


format 转义规则同 consolidation_prompt：字面花括号写 {{ }}，
{messages} / {types} / {usages} / {visibilities} 为占位符。


前缀缓存约束（2026-08-28 起）：``{messages}`` 必须留在模板最末尾，
理由与守卫同 consolidation_prompt.py，不再重复。


紧凑输出（2026-11-25，issue #136）：verification_contract 占候选文本约 72%，生产上限下
截断过半；模型改为只填 content / source_message_ids / statement_kind，谓词与值由
evidence_contract.derive_contract 从 content 机械推导。不要再让模型输出合同字段。

契约硬规则块（2026-10-17 增补）：模板末段枚举服务端闸门
（memory/evidence_contract.py 的 _SELF_REPORT_PATTERNS / _PATTERN 正则）
支持的刻板句型与 statement_kind↔type/polarity 绑定——live 回放实证真实模型
产出的契约全数 unknown、0 accepted，根因是没教契约形状。闸门句型扩缩时须
同步这段枚举；该块属于固定指令，必须留在分隔线之上。
"""


_TYPES = "FACT / PREFERENCE / EVENT / PLAN / RELATION / STYLE / GROUP_CONTEXT"
_USAGES = (
    "TOPIC_START / TOPIC_CONTINUE / ANSWER_CONTEXT / RECOMMEND / PERSONALIZE / "
    "RELATION_CONTEXT / GROUP_CONTEXT / HUMOR / EMOTIONAL_SUPPORT / BOUNDARY_PROTECTION / CONFLICT_AVOID"
)
_VISIBILITIES = "OPEN / CONTEXTUAL / RESTRICTED / INTERNAL"


EXTRACTION_PROMPT = """你将读到一段群聊记录。已经有初步判断认为：这段记录里包含「某个具体用户亲口说出的、关于他自己的」信息。你的任务是把这些信息准确地提取成记忆候选，用 JSON 输出。


你的目标是「不漏」：把每一条用户亲口说出的、关于自己的稳定信息都提取出来。
是否值得长期保存，由后续的独立流程判断，不需要你在这一步顾虑——你只管如实提取。


判断依据是「这句话在描述谁」：
- 描述发言者自身（拥有什么设备、能不能吃什么、住在哪、做什么工作、作息习惯、
  身体状况、家庭情况…）→ 提取
- 描述第三方事物（新闻、别人的产品、他人）→ 不提取
不要因为句子里出现了产品名或地名就当作第三方——「我的显卡是 X」描述的是发言者。


区分「当下状态」与「稳定属性」：
- 只说一次「今天想吃炸鸡」→ EVENT（会变）
- 客观限制/客观事实（过敏、忌口、身体条件、居住地、职业、设备型号、作息规律）
  说一次即成立 → FACT（明天不会变）
判断标准是「这件事明天会不会变」，不是「被说了几次」。


正例（务必学会这类提取）：
消息「我时不时会失眠，所以醒得很早」
→ {{"user_id": "该发言者QQ号", "type": "FACT", "content": "我时不时会失眠",
    "usage_tags": ["ANSWER_CONTEXT"], "visibility": "OPEN",
    "importance": 0.6, "confidence": 0.9,
    "source_message_ids": [123], "statement_kind": "other"}}
消息「早餐一般只是一个馒头，自己家做的」
→ {{"user_id": "该发言者QQ号", "type": "FACT", "content": "早餐一般只是一个馒头",
    "usage_tags": ["ANSWER_CONTEXT", "PERSONALIZE"], "visibility": "OPEN",
    "importance": 0.5, "confidence": 0.9,
    "source_message_ids": [123], "statement_kind": "other"}}


请用以下 JSON 格式回复（不要代码块，直接输出 JSON）：
{{
  "memory_candidates": []
}}


规则：
- user_id 必须是该消息实际发送者的纯数字 QQ 号（例如 123456789），不带「用户()」前缀，
  严禁把 A 的发言归属给 B
- 标注「[这是机器人自己发送的消息，不属于任何用户]」的是机器人自己的发言，只用于理解上下文，
  严禁从中提取任何关于用户的信息
- 记忆类型必须且只能选一个：FACT=稳定事实 / PREFERENCE=明确喜欢或讨厌 / EVENT=重要事件 /
  PLAN=未来计划 / RELATION=人与人稳定互动 / STYLE=交流方式 / GROUP_CONTEXT=群体共同状态
- 用户对「怎么称呼/叫TA」的要求（如「以后叫我X」「别再叫我Y」）固定记为 PREFERENCE，
  不要在 RELATION/PREFERENCE 之间摇摆——同一事实两次类型不同会绕过去重产生重复记忆
- 涉及「不喜欢/讨厌/拒绝/边界/未经允许」等敏感内容时，usage_tags 必须是 BOUNDARY_PROTECTION
  或 CONFLICT_AVOID，visibility 必须是 RESTRICTED，绝不能当作聊天话题
- usage_tags 填这条记忆「将来应该被如何使用」，从这些里选：{usages}
- visibility 从这些里选：{visibilities}
- confidence 表示「这条信息有多确定」：>0.9 用户明确直接陈述、0.7-0.9 强暗示、
  0.4-0.7 有依据但不完全确定。如实标注即可，不要因为不确定就丢弃——低置信候选照常输出，
  由下游闸门决定去留。低于 0.3 的纯猜测才不要输出。
- importance 表示「这条信息对以后理解这个人有多大价值」，与 confidence 无关——
  一件事可以既非常确定又无关紧要：0.7-1.0 长期稳定且影响该怎么跟他相处（过敏忌口、
  职业、居住地、身体状况、明确说出的边界）；0.4-0.7 一般偏好与习惯；
  0.1-0.4 当下状态或琐事（今天想吃什么、临时情绪、一次性的事件）。
  **必须逐条自行判断后填写，不要照抄下面结构示例里的 0.0**——填 0 等于宣告
  这条信息毫无价值，它会被直接丢弃，再高的 confidence 也救不回来。
- content 必须是可理解的自然语言，不要只写关键词
- content 必须逐字复制一个最短、完整的原文支持片段；不要改写、归纳或补全
- 每条候选必须附 statement_kind，表示这句话是什么性质：self_report / explicit_preference /
  identity_state / plan_intent / ability_habit / past_event；不确定主体、条件/假设、疑问、
  转述、引用、玩笑或角色扮演时一律填 other——服务端据此拒绝写入正式记忆
- 每条候选只对应一条来源消息：source_message_ids 只填一个本批消息 ID，
  content 必须是该条消息原文的连续逐字子串
- 不要输出 verification_contract、predicate_key 或 canonical_value：服务端从 content 机械推导
- 不要输出 evidence 或任何未列出的字段（节省输出长度）
- 绝对不要编造记录里没有的信息。刷屏、复读、表情、单字附和不包含任何可提取信息，跳过它们
- 一次性玩笑不要提取


每条候选的完整结构：
{{
  "user_id": "纯数字QQ号",
  "type": "{types}",
  "content": "可长期记忆的事实或偏好描述",
  "usage_tags": ["{usages}"],
  "visibility": "{visibilities}",
  "behavior_rule": "涉及边界/行为约束时写明；否则省略",
  "importance": 0.0,
  "confidence": 0.0,
  "source_message_ids": [123],
  "statement_kind": "self_report"
}}


契约硬规则（服务端按固定句型逐字审核 content，完全命中且 statement_kind 一致才可能被判 accepted）：

- 保持原文语言：英文消息就用下列英文句型逐字复制（如 I live in X），中文消息用中文句型；
  绝不要把原文翻译成另一种语言再填 content——翻译后不是原文子串，必被拒绝

服务端支持的刻板句型（content 必须逐字是其中一种；X 代表值段；
statement_kind 与 type 必须按所属组填写）：
- self_report（type=FACT）：「我住在X」「我居住在X」「我现在/目前住在X」「我来自X」「我出生于X」
  「我叫X」「我在X工作」；「I live in X」「I am from X」「I'm from X」「My name is X」
- explicit_preference（type=PREFERENCE）：「我喜欢X」「我偏好X」「我不喜欢X」「我讨厌X」；
  「I like X」「I prefer X」「I don't like X」「I dislike X」
- identity_state（type=FACT）：「我是X」「我有X」；「I am X」「I have X」
- plan_intent（type=PLAN）：「我打算X」「我想X」「我要X」「我正在X」；
  「I'm going to X」「I'm planning on/to X」「I want to X」
- ability_habit（type=FACT）：「我会X」（能力，不是将来）；「I can X」「I play X」「I sing X」
- past_event（type=FACT）：「我以前/曾经X」；「I used to X」「I went to X」「I had X」
- 其他第一人称陈述取**逐字原文**（含缩略/过去式），不要改写成三人称

值段硬规则（全部刻板句型通用，违反任何一条契约都不会 accepted，候选本身照常输出）：
- 值段内不得出现「你/您」（夸赞他人的「我喜欢你画画」不是说话者的偏好）
- 值段不得是占位符 X 或短于 2 个字符

content 与值段硬规则（违反任何一条都不会 accepted，候选本身照常输出）：
- content 只取刻板句本身，遇到逗号/分号/后续分句立即截断：
  「我叫小艾，以后多指教」→ content=「我叫小艾」
- 但不要从条件、转述、引用句里截出一句：「如果我住在杭州就好了」「他说我住在杭州」
  不是说话者的事实，statement_kind 填 other
- 句尾至多保留一个 。或 ！；逗号、分号、问号结尾不会被接受
- content 中不要出现「如果/可能/也许/听说/据说/玩笑」等词或任何引号

反例（真实出现过的失败形态，不要再犯）：
- ✗ content=「我叫小艾，以后多指教」（整句带尾巴）→ 应截为「我叫小艾」
- ✗ 自我介绍「我叫小艾」标成 PREFERENCE → 应为 self_report + FACT
- ✗ 「我喜欢你的画」标成说话者偏好 → 值段含「你」，是夸赞他人，不会 accepted

与称呼要求的边界：发言者介绍自己「我叫X」按 self_report / FACT
输出；发言者要求别人怎么称呼 TA（「以后叫我X」「别再叫我Y」）维持 PREFERENCE
（保证去重稳定），当前不会被判 accepted，照常输出即可，不要硬凑刻板句型。

其余非刻板句型（身体状况、习惯、经历、设备等）仍然照常提取，目标是不漏——
它们不会被 accepted，由服务端按未核验处理，不需要你回避或改写原文。

===== 以上为固定规则；以下是本次待分析的数据 =====

群聊消息：
{messages}
"""


def format_extraction_prompt(messages: str) -> str:
    """填充提取 prompt：注入消息批次与 v2 分类枚举。"""
    return EXTRACTION_PROMPT.format(
        messages=messages,
        types=_TYPES,
        usages=_USAGES,
        visibilities=_VISIBILITIES,
    )
