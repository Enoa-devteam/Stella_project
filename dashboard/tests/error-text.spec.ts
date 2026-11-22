import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { errorText } from '@/utils/errorText';

describe('errorText', () => {
  it('keeps a string rejection from a Tauri command', () => {
    expect(errorText('启动失败（code 1）')).toBe('启动失败（code 1）');
  });

  it('reads Error messages and tolerates empty rejections', () => {
    expect(errorText(new Error('boom'))).toBe('boom');
    expect(errorText(undefined)).toBe('undefined');
    expect(errorText({ message: 'shaped' })).toBe('shaped');
  });

  it('is what the desktop start page uses: a cast crashed on string rejections', () => {
    const page = readFileSync('src/views/BackendOfflinePage.vue', 'utf-8');
    expect(page).not.toContain('(err as Error).message');
    expect(page).toContain('errorText(err)');
  });
});
