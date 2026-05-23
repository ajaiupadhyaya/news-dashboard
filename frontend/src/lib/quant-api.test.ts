import { describe, expect, test } from 'vitest';
import { api } from './api';

describe('quant api surface', () => {
  test('all quant methods exist', () => {
    expect(typeof api.quantOverview).toBe('function');
    expect(typeof api.quantStrategy).toBe('function');
    expect(typeof api.quantStrategyTrades).toBe('function');
    expect(typeof api.quantRecompute).toBe('function');
    expect(typeof api.quantRun).toBe('function');
  });
});
