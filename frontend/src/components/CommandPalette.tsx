import { useMemo, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { spring } from '../design/motion';
import { useReducedMotion } from '../lib/useReducedMotion';

interface Destination {
  label: string;
  hint: string;
  to: string;
}

/** Fixed destinations the palette can always jump to. */
const STATIC_DESTINATIONS: Destination[] = [
  { label: 'Dashboard', hint: 'Home', to: '/' },
  { label: 'Finance Markets', hint: 'Page', to: '/finance' },
  { label: 'Inflation (CPI)', hint: 'Indicator', to: '/economics/CPIAUCSL' },
  { label: 'Unemployment Rate', hint: 'Indicator', to: '/economics/UNRATE' },
  { label: 'Nonfarm Payrolls', hint: 'Indicator', to: '/economics/PAYEMS' },
  { label: 'Real GDP Growth', hint: 'Indicator',
    to: '/economics/A191RL1Q225SBEA' },
  { label: 'Fed Funds Rate', hint: 'Indicator', to: '/economics/FEDFUNDS' },
  { label: '10-Year Treasury', hint: 'Indicator', to: '/economics/DGS10' },
  { label: 'Quant Lab', hint: 'Page', to: '/quant' },
  { label: 'SMA Crossover', hint: 'Strategy', to: '/quant/strategy/sma-crossover' },
  { label: 'RSI Mean Reversion', hint: 'Strategy', to: '/quant/strategy/rsi-mean-reversion' },
  { label: 'Cross-Sectional Momentum', hint: 'Strategy', to: '/quant/strategy/cross-sectional-momentum' },
  { label: 'Pairs Trading', hint: 'Strategy', to: '/quant/strategy/pairs-trading' },
  { label: 'Bollinger Breakout', hint: 'Strategy', to: '/quant/strategy/bollinger-breakout' },
  { label: 'News-Sentiment Momentum', hint: 'Strategy', to: '/quant/strategy/news-sentiment-momentum' },
  { label: 'Macro-Regime Overlay', hint: 'Strategy', to: '/quant/strategy/macro-regime-overlay' },
  { label: 'Multi-Factor Combo', hint: 'Strategy', to: '/quant/strategy/multi-factor-combo' },
  { label: 'Buy & Hold SPY', hint: 'Strategy', to: '/quant/strategy/buy-hold-spy' },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

/** A ⌘K command palette — jump to an instrument, an indicator, or home. */
export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const reduced = useReducedMotion();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);

  const items = useMemo<Destination[]>(() => {
    const q = query.trim();
    const matches = STATIC_DESTINATIONS.filter((d) =>
      d.label.toLowerCase().includes(q.toLowerCase()),
    );
    if (q) {
      const ticker = q.toUpperCase().replace(/[^A-Z0-9.\-^]/g, '');
      if (ticker) {
        matches.unshift({
          label: `View instrument: ${ticker}`,
          hint: 'Instrument',
          to: `/finance/${ticker}`,
        });
      }
    }
    return matches;
  }, [query]);

  if (!open) return null;

  function go(dest: Destination | undefined) {
    if (!dest) return;
    onClose();
    setQuery('');
    setActive(0);
    navigate(dest.to, { viewTransition: true });
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(items.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      go(items[active]);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center
                 bg-bg/70 pt-[12vh]"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: reduced ? 0 : -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={reduced ? { duration: 0 } : spring.gentle}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg overflow-hidden rounded-lg border
                   border-border-strong bg-surface shadow-2xl"
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          placeholder="Search instruments, indicators…"
          aria-label="Command palette search"
          className="w-full border-b border-border bg-transparent px-4 py-3
                     text-sm text-ink outline-none placeholder:text-ink-mute"
        />
        <ul className="max-h-80 overflow-y-auto py-1">
          {items.length === 0 && (
            <li className="px-4 py-3 text-xs text-ink-mute">No matches.</li>
          )}
          {items.map((dest, i) => (
            <li key={dest.to}>
              <button
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => go(dest)}
                className={`flex w-full items-center justify-between px-4 py-2
                            text-left text-sm transition-colors ${
                              i === active
                                ? 'bg-raised text-ink'
                                : 'text-ink-soft'
                            }`}
              >
                <span>{dest.label}</span>
                <span className="font-mono text-[10px] text-ink-mute uppercase">
                  {dest.hint}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </motion.div>
    </div>
  );
}
