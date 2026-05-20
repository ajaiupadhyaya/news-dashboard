import type { ReactNode } from 'react';
import { AppBar } from './AppBar';
import { BriefingRibbon } from './BriefingRibbon';

/** The persistent chrome: app bar + briefing ribbon, with routed content below. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-col bg-bg">
      <AppBar />
      <BriefingRibbon />
      {children}
    </div>
  );
}
