# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 Stella Project Contributors
# 全文见项目根目录 LICENSE.
"""发布工具链锁定（release_assets/toolchain.json，WP06）的一致性测试。

锁定值一经发布即成为安装行为指纹的一部分：测试保证 CI 消费、产品
profile 与壳内常量同源，任何漂移在 PR 阶段就失败。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN_PATH = REPO_ROOT / "release_assets" / "toolchain.json"
RELEASE_YML = REPO_ROOT / ".github" / "workflows" / "release.yml"


def _toolchain() -> dict:
    return json.loads(TOOLCHAIN_PATH.read_text(encoding="utf-8"))


def test_toolchain_pins_exact_versions():
    toolchain = _toolchain()
    assert re.fullmatch(r"\d+\.\d+\.\d+", toolchain["tauri_cli"]), (
        "tauri-cli 必须是精确版本，不许 ^/>= 浮动（NSIS 模板随版本漂移）"
    )
    assert re.fullmatch(r"\d+\.\d+(\.\d+)?", toolchain["maturin"])
    assert re.fullmatch(r"[0-9a-f]{40}", toolchain["llama_cpp_commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", toolchain["embedding_commit"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", toolchain["python"])


def test_toolchain_python_matches_shell_constants():
    toolchain = _toolchain()
    text = (REPO_ROOT / "desktop" / "src-tauri" / "src" / "python.rs").read_text(
        encoding="utf-8"
    )
    match = re.search(r'const PY_VER: &str = "([^"]+)"', text)
    assert match and match.group(1) == toolchain["python"], (
        "toolchain.json 的 Python 版本必须与壳内 PY_VER 一致"
    )


def test_toolchain_llama_commit_matches_release_workflow():
    toolchain = _toolchain()
    workflow = RELEASE_YML.read_text(encoding="utf-8")
    match = re.search(r"LLAMA_CPP_COMMIT: ([0-9a-f]{40})", workflow)
    assert match, "release.yml 必须继续钉住 llama.cpp 提交"
    assert match.group(1) == toolchain["llama_cpp_commit"]


def test_release_workflow_pins_llama_ui_assets():
    # 不钉时浅克隆推导出不存在的 b1 并回退浮动 latest（run 44905135423 失败）
    toolchain = _toolchain()
    workflow = RELEASE_YML.read_text(encoding="utf-8")
    match = re.search(r"LLAMA_CPP_UI_VERSION: (b\d+)\n", workflow)
    assert match, "llama.cpp UI 资产版本必须钉住"
    assert match.group(1) == toolchain["llama_cpp_ui_version"]
    assert "ui-version: ${{ env.LLAMA_CPP_UI_VERSION }}" in workflow
    action = (REPO_ROOT / ".github" / "actions" / "llama-cpu-backend" / "action.yml").read_text(
        encoding="utf-8"
    )
    assert "HF_UI_VERSION: ${{ inputs.ui-version }}" in action


def test_llama_backend_cache_key_covers_all_inputs():
    action = (REPO_ROOT / ".github" / "actions" / "llama-cpu-backend" / "action.yml").read_text(
        encoding="utf-8"
    )
    key_part = action.split("- id: restore")[0]
    for token in ("INPUT_COMMIT", "INPUT_UI_VERSION", "build_llama_package.py",
                  "verify_llama_package.py", "OPENSSL_RUNTIME_DIR"):
        assert token in key_part, f"缓存键缺少输入 {token}"
    verify_step = action.split("- name: 校验 Windows CPU backend")[1].split("- name:")[0]
    assert "if:" not in verify_step, "命中缓存也必须重跑校验"


def test_product_profiles_pin_embedding_to_toolchain_commit():
    toolchain = _toolchain()
    commit = toolchain["embedding_commit"]
    for name in ("oneclick-python.json", "oneclick-rust.json"):
        profile_path = REPO_ROOT / "release_assets" / "product-profiles" / name
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        source = profile["default_models"][0]["source"]
        assert f"/resolve/{commit}/" in source, (
            f"{name} 的 embedding source 必须钉在 toolchain.json 的提交上"
        )
        assert "/resolve/main/" not in source, (
            f"{name} 的 embedding source 不得指向浮动 main（WP06）"
        )


def test_release_workflow_consumes_toolchain_locks():
    workflow = RELEASE_YML.read_text(encoding="utf-8")
    assert "toolchain.json" in workflow, "release.yml 必须从 toolchain.json 读锁定值"
    assert "uses: ./.github/actions/install-tauri-cli" in workflow, (
        "tauri-cli 必须经锁定版本的安装 action 安装（替换 ^2 浮动）"
    )
    assert "cargo install tauri-cli" not in workflow, (
        "tauri-cli 不再源码编译（每条矩阵腿 ~10 分钟），改用校验过的官方预编译包"
    )
    assert "maturin==$($toolchain.maturin)" in workflow, (
        "maturin 必须按锁定版本安装（替换 --upgrade 浮动）"
    )
    installer_block = workflow.split("build-installer:")[1].split("build-rust-wheel:")[0]
    assert "setup-python" in installer_block, (
        "build-installer 必须显式 setup-python，不依赖 runner 默认 Python"
    )
    assert workflow.count("$LASTEXITCODE -ne 0") >= 3, (
        "Windows 关键 native 命令后必须立即检查退出码（防后续成功命令盖掉失败）"
    )


def test_tauri_cli_install_action_verifies_pinned_prebuilt():
    toolchain = _toolchain()
    assert re.fullmatch(r"[0-9a-f]{64}", toolchain["tauri_cli_windows_sha256"]), (
        "tauri-cli 预编译包必须钉住 sha256"
    )
    action = (REPO_ROOT / ".github" / "actions" / "install-tauri-cli" / "action.yml").read_text(
        encoding="utf-8"
    )
    assert "tauri-cli-v$version" in action and "$toolchain.tauri_cli" in action
    assert "$toolchain.tauri_cli_windows_sha256" in action, "必须校验预编译包哈希"
    assert '"tauri-cli $version"' in action, "必须校验二进制自报版本"


def test_nsis_compression_is_pinned_per_payload():
    toolchain = _toolchain()
    allowed = {"none", "zlib", "bzip2", "lzma"}
    assert set(toolchain["nsis_compression"]) == {"online", "offline"}
    assert set(toolchain["nsis_compression"].values()) <= allowed
    # none 让 offline EXE 大 31%（1119→1461MiB），只省约 1 分钟构建：v6.4.0 误选过一次
    assert toolchain["nsis_compression"]["offline"] != "none"
    workflow = RELEASE_YML.read_text(encoding="utf-8")
    assert "$toolchain.nsis_compression" in workflow
    assert "--config $override" in workflow, "压缩算法必须经 --config 传给 tauri build"


def test_webview_install_mode_is_offline_safe():
    # offline 必须零联网（2026-09 用户反馈）；online 用引导器避开 280MB 离线运行时
    toolchain = _toolchain()
    modes = toolchain["webview_install_mode"]
    assert modes == {"online": "embedBootstrapper", "offline": "offlineInstaller"}
    workflow = RELEASE_YML.read_text(encoding="utf-8")
    assert "$toolchain.webview_install_mode" in workflow
    assert "offline 安装器必须内嵌 WebView2 离线安装包" in workflow, "offline 腿必须硬校验"
