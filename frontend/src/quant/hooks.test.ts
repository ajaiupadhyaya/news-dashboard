import { describe, expect, test } from 'vitest';
import {
  useQuantOverview, useStrategy, useStrategyTrades,
  useRecompute, useRunStatus,
} from './hooks';

describe('quant hooks', () => {
  test('all hooks are exported', () => {
    expect(typeof useQuantOverview).toBe('function');
    expect(typeof useStrategy).toBe('function');
    expect(typeof useStrategyTrades).toBe('function');
    expect(typeof useRecompute).toBe('function');
    expect(typeof useRunStatus).toBe('function');
  });
});
