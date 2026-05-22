import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';
import { FinancePanel } from '../finance/FinancePanel';
import { EconomicsPanel } from '../economics/EconomicsPanel';

export function Home() {
  return (
    <AppShell>
      <QuadrantGrid
        news={<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />}
        politics={<ComingSoonPanel title="Politics" icon="🏛" phase="Phase 4" />}
        economics={<EconomicsPanel />}
        finance={<FinancePanel />}
      />
    </AppShell>
  );
}
