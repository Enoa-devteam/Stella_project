# SPDX-License-Identifier: AGPL-3.0
# Copyright (c) 2026 stella Project Contributors
# 本文件以 AGPL-3.0 许可证发布，详见项目根目录 LICENSE。
"""干净 Windows 没有 VC++ 运行库：发布二进制必须静态链接或随包携带（v6.4.1）。"""

from __future__ import annotations

import struct
from pathlib import Path

from scripts import build_llama_package, check_windows_crt

ROOT = Path(__file__).resolve().parents[1]


def _pe(*imports: str) -> bytes:
    """最小的 PE32+：一个节，只有导入表。"""
    descriptors = bytearray(20 * (len(imports) + 1))
    names = bytearray()
    base = 0x1000 + len(descriptors)
    for index, name in enumerate(imports):
        struct.pack_into("<I", descriptors, 20 * index + 12, base + len(names))
        names += name.encode("ascii") + b"\0"
    body = bytes(descriptors) + bytes(names)
    image = bytearray(0x200)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x40)
    image[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<H", image, 0x46, 1)
    struct.pack_into("<H", image, 0x54, 0xF0)
    struct.pack_into("<H", image, 0x58, 0x20B)
    struct.pack_into("<I", image, 0x58 + 120, 0x1000)
    struct.pack_into("<IIII", image, 0x58 + 0xF0 + 8, len(body), 0x1000, len(body), 0x200)
    return bytes(image) + body


def test_missing_vc_runtime_is_rejected(tmp_path):
    exe = tmp_path / "stella.exe"
    exe.write_bytes(_pe("KERNEL32.dll", "VCRUNTIME140_1.dll"))
    assert any("VCRUNTIME140_1.dll" in problem for problem in check_windows_crt.check(exe))


def test_app_local_runtime_and_system_ucrt_are_accepted(tmp_path):
    (tmp_path / "llama.dll").write_bytes(
        _pe("MSVCP140.dll", "VCOMP140.DLL", "api-ms-win-crt-heap-l1-1-0.dll")
    )
    (tmp_path / "msvcp140.dll").write_bytes(_pe("KERNEL32.dll"))
    (tmp_path / "vcomp140.dll").write_bytes(_pe("KERNEL32.dll"))
    assert check_windows_crt.check(tmp_path) == []


def test_unreadable_or_missing_target_fails_closed(tmp_path):
    broken = tmp_path / "broken.exe"
    broken.write_bytes(b"not a binary")
    assert check_windows_crt.check(broken)
    assert check_windows_crt.check(tmp_path / "absent.exe")


def test_llama_package_copies_vc_runtime(tmp_path):
    build_dir, output, redist = tmp_path / "build", tmp_path / "out", tmp_path / "redist"
    for directory in (build_dir, output, redist):
        directory.mkdir()
    for name in ("libcrypto-3-x64.dll", "libssl-3-x64.dll"):
        (output / name).write_bytes(b"x")
    (redist / "vcruntime140_1.dll").write_bytes(b"crt")
    build_llama_package._copy_runtime_libraries(
        build_dir,
        build_dir / "llama-server.exe",
        output,
        os_name="windows",
        runtime_dirs=[],
        vc_runtime_dirs=[redist],
    )
    assert (output / "vcruntime140_1.dll").read_bytes() == b"crt"


def test_release_pipeline_enforces_the_crt_gate():
    # tauri-build 2.7+: static CRT via WindowsAttributes; the deprecated env var would override it.
    for shell in ("desktop/src-tauri", "stella-installer/src-tauri"):
        build_rs = (ROOT / shell / "build.rs").read_text(encoding="utf-8")
        assert ".static_vc_runtime(true)" in build_rs, shell
        assert build_rs.index('remove_var("STATIC_VCRUNTIME")') < build_rs.index("tauri_build::try_build("), shell
        assert 'set_var("STATIC_VCRUNTIME"' not in build_rs, shell
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "check_windows_crt.py target/release/stella.exe" in release
    action = (ROOT / ".github/actions/llama-cpu-backend/action.yml").read_text(encoding="utf-8")
    assert "check_windows_crt.py $env:PACKAGE_DIR" in action
