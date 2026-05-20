import { Panel } from './Panel';

interface ComingSoonPanelProps {
  title: string;
  icon: string;
  phase: string;
}

/** Placeholder panel for domains not yet built (News, Politics, Economics). */
export function ComingSoonPanel({ title, icon, phase }: ComingSoonPanelProps) {
  return (
    <Panel title={title} icon={icon}>
      <div className="flex min-h-40 flex-col items-center justify-center gap-1
                      text-center">
        <p className="text-sm text-ink-soft">Arriving in {phase}</p>
        <p className="text-xs text-ink-mute">
          This domain comes online in a later build phase.
        </p>
      </div>
    </Panel>
  );
}
