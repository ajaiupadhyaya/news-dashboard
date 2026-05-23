import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';
import { Panel } from '../components/Panel';
import { FinancePanel } from '../finance/FinancePanel';
import { EconomicsPanel } from '../economics/EconomicsPanel';
import { NewsPanel } from '../news/NewsPanel';

export function Home() {
  return (
    <AppShell>
      <QuadrantGrid
        news={<NewsPanel />}
        politics={<ComingSoonPanel title="Politics" icon="🏛" phase="Phase 4" />}
        economics={<EconomicsPanel />}
        finance={<FinancePanel />}
      />
      <div className="px-4 pb-4">
        <Panel title="Quant Lab" icon="📐" href="/quant">
          <div className="flex min-h-24 flex-col items-center justify-center gap-1 text-center">
            <p className="text-sm text-ink-soft">9 strategies · S&amp;P 500 + market-neutral pairs</p>
            <p className="text-xs text-ink-mute">Backtested walk-forward with live forward-step execution.</p>
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
