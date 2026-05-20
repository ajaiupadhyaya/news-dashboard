import type { ReactNode } from 'react';

interface QuadrantGridProps {
  news: ReactNode;
  politics: ReactNode;
  economics: ReactNode;
  finance: ReactNode;
}

/** The 2×2 domain grid; collapses to a single column on small screens. */
export function QuadrantGrid({
  news,
  politics,
  economics,
  finance,
}: QuadrantGridProps) {
  return (
    <div className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-2">
      {news}
      {politics}
      {economics}
      {finance}
    </div>
  );
}
