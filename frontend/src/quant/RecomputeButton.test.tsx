import { screen, render, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, type Mock } from 'vitest';
import { RecomputeButton } from './RecomputeButton';

// ---------------------------------------------------------------------------
// Mock ./hooks before any imports of the module under test are resolved.
// ---------------------------------------------------------------------------
vi.mock('./hooks', () => ({
  useRecompute: vi.fn(),
  useRunStatus: vi.fn(),
}));

// Import mocks AFTER vi.mock declaration so the factory runs first.
import { useRecompute, useRunStatus } from './hooks';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMutate(onSuccess?: (data: { run_id: number; status: string }) => void) {
  return vi.fn((_vars: unknown, options?: { onSuccess?: (d: { run_id: number; status: string }) => void; onError?: (e: unknown) => void }) => {
    if (options?.onSuccess) {
      options.onSuccess({ run_id: 42, status: 'pending' });
    } else if (onSuccess) {
      onSuccess({ run_id: 42, status: 'pending' });
    }
  });
}

function setupMocks({
  runStatus = null,
}: {
  runStatus?: { status: string; finished_at?: string | null; error?: string | null; progress?: { windows_done?: number; windows_total?: number } } | null;
} = {}) {
  (useRecompute as Mock).mockReturnValue({
    mutate: makeMutate(),
    isPending: false,
  });
  (useRunStatus as Mock).mockReturnValue({
    data: runStatus,
    isLoading: false,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test('renders idle state with "Recompute backtest" label', () => {
  setupMocks();
  render(<RecomputeButton slug="sma-crossover" />);
  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Recompute backtest');
  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'idle');
});

test('clicking in idle state triggers mutate and transitions to polling', async () => {
  setupMocks();
  const user = userEvent.setup();
  render(<RecomputeButton slug="sma-crossover" />);

  await user.click(screen.getByTestId('recompute-btn'));

  // After click, mutate was called with onSuccess which fires synchronously,
  // setting runId=42 and phase=polling.
  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'polling');
  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Recomputing…');
});

test('polling state shows windows progress when available', async () => {
  // First render idle, then re-mock to have run status with progress.
  setupMocks();
  const user = userEvent.setup();
  const { rerender } = render(<RecomputeButton slug="sma-crossover" />);

  await user.click(screen.getByTestId('recompute-btn'));

  // Now mock run status to return progress data.
  (useRunStatus as Mock).mockReturnValue({
    data: {
      status: 'running',
      finished_at: null,
      error: null,
      progress: { windows_done: 3, windows_total: 10 },
    },
    isLoading: false,
  });

  rerender(<RecomputeButton slug="sma-crossover" />);

  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Recomputing… (3/10)');
});

test('transitions to success when run status becomes success', async () => {
  setupMocks();
  const user = userEvent.setup();
  const { rerender } = render(<RecomputeButton slug="sma-crossover" />);

  await user.click(screen.getByTestId('recompute-btn'));

  // Mock the run status to return success.
  (useRunStatus as Mock).mockReturnValue({
    data: {
      status: 'success',
      finished_at: '2026-05-23T10:00:00Z',
      error: null,
      progress: { windows_done: 10, windows_total: 10 },
    },
    isLoading: false,
  });

  act(() => {
    rerender(<RecomputeButton slug="sma-crossover" />);
  });

  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'success');
  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Last recomputed:');
});

test('transitions to failed when run status becomes failed', async () => {
  setupMocks();
  const user = userEvent.setup();
  const { rerender } = render(<RecomputeButton slug="sma-crossover" />);

  await user.click(screen.getByTestId('recompute-btn'));

  (useRunStatus as Mock).mockReturnValue({
    data: {
      status: 'failed',
      finished_at: null,
      error: 'Backtest computation error',
      progress: {},
    },
    isLoading: false,
  });

  act(() => {
    rerender(<RecomputeButton slug="sma-crossover" />);
  });

  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'failed');
  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Recompute failed:');
  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Backtest computation error');
});

test('clicking success state resets to idle', async () => {
  setupMocks();
  const user = userEvent.setup();
  const { rerender } = render(<RecomputeButton slug="sma-crossover" />);

  // Drive to success.
  await user.click(screen.getByTestId('recompute-btn'));

  (useRunStatus as Mock).mockReturnValue({
    data: {
      status: 'success',
      finished_at: '2026-05-23T10:00:00Z',
      error: null,
      progress: {},
    },
    isLoading: false,
  });

  act(() => {
    rerender(<RecomputeButton slug="sma-crossover" />);
  });

  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'success');

  // Click again to reset.
  await user.click(screen.getByTestId('recompute-btn'));
  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'idle');
  expect(screen.getByTestId('recompute-btn')).toHaveTextContent('Recompute backtest');
});

test('clicking failed state resets to idle', async () => {
  setupMocks();
  const user = userEvent.setup();
  const { rerender } = render(<RecomputeButton slug="sma-crossover" />);

  await user.click(screen.getByTestId('recompute-btn'));

  (useRunStatus as Mock).mockReturnValue({
    data: {
      status: 'failed',
      finished_at: null,
      error: 'Some error',
      progress: {},
    },
    isLoading: false,
  });

  act(() => {
    rerender(<RecomputeButton slug="sma-crossover" />);
  });

  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'failed');

  await user.click(screen.getByTestId('recompute-btn'));
  expect(screen.getByTestId('recompute-btn')).toHaveAttribute('data-phase', 'idle');
});
