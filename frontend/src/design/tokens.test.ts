import { tokens } from './tokens';

test('exposes the semantic color palette', () => {
  expect(tokens.color.up).toBe('#3fb950');
  expect(tokens.color.down).toBe('#f0506a');
  expect(tokens.color.accent).toBe('#5b9dff');
});

test('exposes surface and ink colors used by charts', () => {
  for (const key of ['bg', 'surface', 'raised', 'border', 'ink', 'inkSoft', 'inkMute']) {
    expect(tokens.color[key as keyof typeof tokens.color]).toMatch(/^#[0-9a-f]{6}$/i);
  }
});

test('exposes font stacks', () => {
  expect(tokens.font.mono).toContain('JetBrains Mono');
  expect(tokens.font.sans).toContain('Inter');
});
