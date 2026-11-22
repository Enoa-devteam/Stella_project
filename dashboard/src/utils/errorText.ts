// SPDX-License-Identifier: AGPL-3.0
// Copyright (c) 2026 stella Project Contributors
// 本文件以 AGPL-3.0 许可证发布，全文见项目根目录 LICENSE.

/**
 * 任意 rejection → 可展示文本。Tauri 命令以**字符串**而非 Error 拒绝：
 * 按 Error 强转会拿到 undefined，catch 自身再抛错，启动页永远停在转圈。
 */
export function errorText(err: unknown): string {
  if (typeof err === 'string') return err;
  const message = (err as { message?: unknown } | null | undefined)?.message;
  return typeof message === 'string' ? message : String(err);
}
