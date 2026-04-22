import React from 'react';

export default function SkeletonCard() {
  return (
    <div className="min-w-[320px] bg-bg-card rounded-lg border border-border p-4 animate-pulse">
      <div className="h-32 bg-bg-card-hover rounded" />
    </div>
  );
}