import React from "react";

export const Skeleton: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div className={`animate-pulse rounded-lg bg-slate-700/60 ${className}`} />
);

export const TruckTypeCardSkeleton: React.FC = () => (
  <div className="rounded-2xl border border-slate-700/80 bg-slate-800/50 p-4 space-y-3">
    <Skeleton className="h-36 w-full" />
    <Skeleton className="h-5 w-2/3" />
    <Skeleton className="h-4 w-full" />
    <Skeleton className="h-4 w-4/5" />
  </div>
);
