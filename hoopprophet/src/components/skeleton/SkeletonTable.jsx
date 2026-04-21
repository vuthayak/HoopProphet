export default function SkeletonTable({ rows = 5 }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-8 bg-bg-card-hover rounded" />
      ))}
    </div>
  );
}