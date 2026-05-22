import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';
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
    </AppShell>
  );
}
