// 首启进度（桌面壳 read_start_progress）的解析与展示文本。
//
// Rust 命令返回 `Result<String, String>`，Tauri 把 JSON **文本**原样交给前端；
// tauriBridge.invoke 不做解析。2026-09-25 起加载视图直接把这段字符串当对象用，
// `bootstrap` / `prepare` 恒为 undefined，实时进度行从未显示（2026-11-24 Sandbox 实测）。

export interface BootProgress {
  state?: string;
  current?: string;
  completed?: string[];
  error?: string;
}

export interface StartProgress {
  bootstrap: BootProgress | null;
  prepare: string | null;
}

/** 接受 JSON 文本（当前 Rust 返回形态）或已解析对象；无法解析返回 null。 */
export function parseStartProgress(raw: unknown): StartProgress | null {
  let value: unknown = raw;
  if (typeof raw === 'string') {
    try {
      value = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (!value || typeof value !== 'object') return null;
  const obj = value as { bootstrap?: unknown; prepare?: unknown };
  const bootstrap =
    obj.bootstrap && typeof obj.bootstrap === 'object' ? (obj.bootstrap as BootProgress) : null;
  const prepare = typeof obj.prepare === 'string' && obj.prepare ? obj.prepare : null;
  return { bootstrap, prepare };
}

/** 加载视图的实时进度行：组件失败 > 组件进行中 > 运行时文本；都没有返回空串。 */
export function startProgressLine(lp: StartProgress | null): string {
  if (!lp) return '';
  if (lp.bootstrap?.state === 'failed') {
    return `组件安装失败：${lp.bootstrap.error || lp.bootstrap.current || '未知原因'}`;
  }
  if (lp.bootstrap?.current) {
    const done = lp.bootstrap.completed?.length ?? 0;
    return `正在安装组件：${lp.bootstrap.current}（已完成 ${done} 项）`;
  }
  return lp.prepare || '';
}
