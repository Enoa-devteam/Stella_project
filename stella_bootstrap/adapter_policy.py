# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 Stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE。
"""Adapter availability rules shared by the control plane and Bot runtime."""

import sys

BLOCKED_ADAPTERS = {
    "nonebot_adapter_walleq": "walleQ",
    "nonebot.adapters.ntchat": "ntchat",
    "nonebot.adapters.mail": "mailSecurityCompatibility",
}

# Stella core supports only OneBot V11 and OneBot V12 (decision in
# https://github.com/Enoa-devteam/stella_project/issues/134). Other platforms are planned
# for a separately maintained adapter project. These adapters are short-circuited
# here: boot skips them, the Platforms page shows them as unavailable, and enabling
# them is refused. Their legacy integration code in core/transport/adapters is left
# in place but is not reachable at runtime.
UNSUPPORTED_IN_CORE_ADAPTERS = dict.fromkeys(
    (
        "nonebot.adapters.ding",
        "nonebot.adapters.feishu",
        "nonebot.adapters.telegram",
        "nonebot.adapters.qq",
        "nonebot.adapters.kaiheila",
        "nonebot.adapters.mirai",
        "nonebot.adapters.console",
        "nonebot.adapters.github",
        "nonebot.adapters.minecraft",
        "nonebot.adapters.bilibili",
        "nonebot.adapters.villa",
        "nonebot.adapters.red",
        "nonebot.adapters.discord",
        "nonebot.adapters.satori",
        "nonebot.adapters.dodo",
        "nonebot.adapters.rocketchat",
        "nonebot.adapters.kritor",
        "nonebot_adapter_tailchat",
        "nonebot.adapters.heybox",
        "nonebot.adapters.wxmp",
        "nonebot.adapters.milky",
        "nonebot.adapters.efchat",
        "nonebot.adapters.vocechat",
        "nonebot.adapters.bilibili_live",
        "nonebot.adapters.yunhu",
        "nonebot.adapters.wxclaw",
        "nonebot.adapters.matrix",
    ),
    "unsupportedInCore",
)

# Temporarily disabled adapters (none right now). OneBot V12 is enabled; it shares
# the installed nonebot-adapter-onebot package with V11 and enters through the
# transport-neutral ingress (stella_project/plugins/bot_main/onebot_v12_gateway.py).
TEMPORARILY_DISABLED_ADAPTERS: dict[str, str] = {}


def unavailable_adapter_reasons() -> dict[str, str]:
    """Return adapters blocked by policy, unsupported in core, disabled, or unsupported here."""
    unavailable = {
        **UNSUPPORTED_IN_CORE_ADAPTERS,
        **TEMPORARILY_DISABLED_ADAPTERS,
        **BLOCKED_ADAPTERS,
    }
    if sys.version_info < (3, 11) and "nonebot.adapters.heybox" not in unavailable:
        unavailable["nonebot.adapters.heybox"] = "requiresPython311"
    return unavailable
