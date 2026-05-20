import { render, screen } from '@testing-library/react';
import { Panel } from './Panel';
import { ComingSoonPanel } from './ComingSoonPanel';
import { PanelSkeleton } from './PanelSkeleton';
import { QuadrantGrid } from './QuadrantGrid';
import { AppShell } from './AppShell';

test('Panel renders its title, action, and children', () => {
  render(
    <Panel title="Finance" icon="💹" action={<span>act</span>}>
      <div>body</div>
    </Panel>,
  );
  expect(screen.getByText('Finance')).toBeInTheDocument();
  expect(screen.getByText('act')).toBeInTheDocument();
  expect(screen.getByText('body')).toBeInTheDocument();
});

test('ComingSoonPanel names the domain and its arrival phase', () => {
  render(<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />);
  expect(screen.getByText('News')).toBeInTheDocument();
  expect(screen.getByText(/Phase 3/)).toBeInTheDocument();
});

test('PanelSkeleton exposes a loading status', () => {
  render(<PanelSkeleton rows={3} />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('QuadrantGrid renders all four domain slots', () => {
  render(
    <QuadrantGrid
      news={<div>N</div>}
      politics={<div>P</div>}
      economics={<div>E</div>}
      finance={<div>F</div>}
    />,
  );
  for (const t of ['N', 'P', 'E', 'F']) {
    expect(screen.getByText(t)).toBeInTheDocument();
  }
});

test('AppShell renders the app bar, briefing ribbon, and children', () => {
  render(<AppShell><div>shell-body</div></AppShell>);
  expect(screen.getByText('NMD')).toBeInTheDocument();
  expect(screen.getByText(/Daily Briefing/i)).toBeInTheDocument();
  expect(screen.getByText('shell-body')).toBeInTheDocument();
});
