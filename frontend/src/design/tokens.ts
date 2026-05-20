/**
 * Design tokens, mirrored here in TypeScript so D3/SVG code (which renders
 * attributes, not classes) can use the exact same palette as the CSS in
 * `index.css`. The CSS `@theme` block is the source of truth for Tailwind
 * utilities; this object is the source of truth for chart code. Keep them
 * in sync when colors change.
 */
export const tokens = {
  color: {
    bg: '#0a0c10',
    surface: '#12151c',
    raised: '#171b24',
    border: '#232834',
    borderStrong: '#2f3645',
    ink: '#e6e9ef',
    inkSoft: '#9aa3b2',
    inkMute: '#5f6878',
    accent: '#5b9dff',
    up: '#3fb950',
    down: '#f0506a',
    flat: '#8b94a3',
  },
  font: {
    sans: '"Inter Variable", system-ui, -apple-system, sans-serif',
    mono: '"JetBrains Mono Variable", ui-monospace, "SF Mono", monospace',
  },
} as const;
