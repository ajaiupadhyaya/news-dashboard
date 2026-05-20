import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';
import { FinancePanel } from '../finance/FinancePanel';

export function Home() {
  return (
    <AppShell>
      <QuadrantGrid
        news={<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />}
        politics={<ComingSoonPanel title="Politics" icon="🏛" phase="Phase 4" />}
        economics={<ComingSoonPanel title="Economics" icon="📊" phase="Phase 2" />}
        finance={<FinancePanel />}
      />
    </AppShell>
  );
}
