import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { AppBar } from './AppBar';
import { BriefingRibbon } from './BriefingRibbon';
import { CommandPalette } from './CommandPalette';

/** The persistent chrome: app bar + briefing ribbon, with routed content
 *  below, plus the ⌘K command palette. */
export function AppShell({ children }: { children: ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex min-h-full flex-col bg-bg">
      <AppBar onOpenSearch={() => setSearchOpen(true)} />
      <BriefingRibbon />
      {children}
      <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}
