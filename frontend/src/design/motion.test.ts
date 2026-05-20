import { spring, duration, fadeRise } from './motion';

test('spring presets are spring-typed transitions', () => {
  for (const preset of [spring.smooth, spring.snappy, spring.gentle]) {
    expect(preset.type).toBe('spring');
    expect(typeof preset.stiffness).toBe('number');
  }
});

test('durations are ordered fast < base < slow', () => {
  expect(duration.fast).toBeLessThan(duration.base);
  expect(duration.base).toBeLessThan(duration.slow);
});

test('fadeRise enters from below and fades in', () => {
  expect(fadeRise.initial).toEqual({ opacity: 0, y: 8 });
  expect(fadeRise.animate).toEqual({ opacity: 1, y: 0 });
});
