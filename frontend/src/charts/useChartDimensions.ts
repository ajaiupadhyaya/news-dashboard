import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

export interface Dimensions {
  width: number;
  height: number;
}

/**
 * Observe an element's size with a ResizeObserver. Returns a ref to attach
 * and the live dimensions, starting from `fallback` until first measured.
 */
export function useChartDimensions<T extends Element>(
  fallback: Dimensions = { width: 640, height: 320 },
): [RefObject<T | null>, Dimensions] {
  const ref = useRef<T>(null);
  const [dims, setDims] = useState<Dimensions>(fallback);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const box = entries[0]?.contentRect;
      if (box && box.width > 0 && box.height > 0) {
        setDims({ width: box.width, height: box.height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return [ref, dims];
}
