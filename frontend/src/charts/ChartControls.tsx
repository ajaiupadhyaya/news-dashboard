import { clsx } from 'clsx';

export const TIMEFRAMES = ['1mo', '3mo', '6mo', '1y', '5y', 'max'] as const;
export type Timeframe = (typeof TIMEFRAMES)[number];

const TIMEFRAME_LABEL: Record<Timeframe, string> = {
  '1mo': '1M', '3mo': '3M', '6mo': '6M', '1y': '1Y', '5y': '5Y', max: 'MAX',
};

export const CHART_TYPES = ['candle', 'line', 'area'] as const;
export type ChartType = (typeof CHART_TYPES)[number];

const CHART_TYPE_LABEL: Record<ChartType, string> = {
  candle: 'Candles', line: 'Line', area: 'Area',
};

interface SegmentedProps<T extends string> {
  options: readonly T[];
  labels: Record<T, string>;
  value: T;
  onChange: (next: T) => void;
  ariaLabel: string;
}

/** A small segmented button group — the shared look for chart controls. */
function Segmented<T extends string>({
  options, labels, value, onChange, ariaLabel,
}: SegmentedProps<T>) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className="flex gap-0.5 rounded-md border border-border bg-raised p-0.5"
    >
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          aria-pressed={value === opt}
          onClick={() => onChange(opt)}
          className={clsx(
            'rounded px-2 py-0.5 font-mono text-[10px] transition-colors',
            value === opt
              ? 'bg-accent text-bg'
              : 'text-ink-mute hover:text-ink',
          )}
        >
          {labels[opt]}
        </button>
      ))}
    </div>
  );
}

/** Timeframe selector — 1M / 3M / 6M / 1Y / 5Y / MAX. */
export function TimeframeControl({
  value, onChange,
}: {
  value: Timeframe;
  onChange: (next: Timeframe) => void;
}) {
  return (
    <Segmented
      options={TIMEFRAMES}
      labels={TIMEFRAME_LABEL}
      value={value}
      onChange={onChange}
      ariaLabel="Timeframe"
    />
  );
}

/** Chart-type toggle — Candles / Line / Area. */
export function ChartTypeToggle({
  value, onChange,
}: {
  value: ChartType;
  onChange: (next: ChartType) => void;
}) {
  return (
    <Segmented
      options={CHART_TYPES}
      labels={CHART_TYPE_LABEL}
      value={value}
      onChange={onChange}
      ariaLabel="Chart type"
    />
  );
}
