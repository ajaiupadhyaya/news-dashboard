interface PanelSkeletonProps {
  rows?: number;
}

/** Shimmer placeholder shown while a panel's data loads. */
export function PanelSkeleton({ rows = 4 }: PanelSkeletonProps) {
  return (
    <div role="status" aria-label="Loading" className="flex flex-col gap-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-6 animate-pulse rounded-md bg-raised" />
      ))}
    </div>
  );
}
