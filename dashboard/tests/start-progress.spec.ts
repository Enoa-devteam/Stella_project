import { describe, expect, it } from 'vitest';
import { parseStartProgress, startProgressLine } from '@/utils/startProgress';

// read_start_progress（desktop/src-tauri/src/commands.rs）返回的就是这种 JSON 文本。
const rustText = (bootstrap: string, prepare: string | null) =>
  `{"bootstrap": ${bootstrap}, "prepare": ${JSON.stringify(prepare)}}`;

describe('parseStartProgress', () => {
  it('parses the JSON text the Rust command returns (the shape the old code used as an object)', () => {
    const lp = parseStartProgress(
      rustText(
        '{"completed": [], "current": "llama-cpu", "profile": "oneclick-python", "schema_version": 1, "state": "running"}',
        null,
      ),
    );
    expect(lp?.bootstrap?.current).toBe('llama-cpu');
    expect(startProgressLine(lp)).toBe('正在安装组件：llama-cpu（已完成 0 项）');
  });

  it('shows runtime text while no component is installing', () => {
    const lp = parseStartProgress(rustText('null', '正在安装依赖（首次约 1-2 分钟）…'));
    expect(lp).toEqual({ bootstrap: null, prepare: '正在安装依赖（首次约 1-2 分钟）…' });
    expect(startProgressLine(lp)).toBe('正在安装依赖（首次约 1-2 分钟）…');
  });

  it('reports a failed component with its error', () => {
    const lp = parseStartProgress(
      rustText('{"completed": [], "current": "", "error": "llama-cpu 下载失败：HTTP 404", "state": "failed"}', null),
    );
    expect(startProgressLine(lp)).toBe('组件安装失败：llama-cpu 下载失败：HTTP 404');
  });

  it('still accepts an already-parsed object', () => {
    const lp = parseStartProgress({ bootstrap: null, prepare: '正在安装 pip…' });
    expect(startProgressLine(lp)).toBe('正在安装 pip…');
  });

  it('falls back to no line on empty or malformed input', () => {
    expect(startProgressLine(parseStartProgress(rustText('null', null)))).toBe('');
    expect(parseStartProgress('not json')).toBeNull();
    expect(parseStartProgress(null)).toBeNull();
    expect(startProgressLine(null)).toBe('');
  });
});
