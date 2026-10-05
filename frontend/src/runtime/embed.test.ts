import { describe, expect, it } from 'vitest';
import { embedSnippet } from './embed';

describe('embedSnippet', () => {
  it('is a single-line iframe with the manifest and profile encoded', () => {
    const s = embedSnippet('https://play.example', 'm_src_demo_standard', { city: 'bengaluru', locale: 'hi-IN' });
    expect(s).not.toContain('\n');
    expect(s).not.toMatch(/<script/i);
    expect(s).toMatch(/^<iframe src="https:\/\/play\.example\/embed\.html\?manifest=m_src_demo_standard&city=bengaluru&locale=hi-IN"/);
  });
});
