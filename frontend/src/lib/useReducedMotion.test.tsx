import { renderHook } from '@testing-library/react';
import { useReducedMotion, useChartAnimationMs } from './useReducedMotion';

test('useReducedMotion returns a boolean', () => {
  const { result } = renderHook(() => useReducedMotion());
  expect(typeof result.current).toBe('boolean');
});

test('useChartAnimationMs returns the base duration when motion is allowed', () => {
  const { result } = renderHook(() => useChartAnimationMs(400));
  expect(result.current).toBe(400);
});
