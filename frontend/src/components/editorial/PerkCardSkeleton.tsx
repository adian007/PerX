export function PerkCardSkeleton() {
  return (
    <div className="flex flex-col border border-border bg-paper">
      <div className="space-y-3 p-6 pb-3">
        <div className="h-6 w-3/4 animate-pulse bg-ink/5" />
        <div className="h-4 w-1/3 animate-pulse bg-ink/5" />
      </div>
      <div className="flex-1 px-6 pb-6">
        <div className="h-16 animate-pulse bg-ink/5" />
      </div>
      <div className="flex gap-2 p-6 pt-0">
        <div className="h-10 w-24 animate-pulse bg-ink/5" />
        <div className="h-10 w-28 animate-pulse bg-ink/5" />
      </div>
    </div>
  )
}
