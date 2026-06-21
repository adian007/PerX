import { cn } from '@/lib/utils'

interface StarRatingProps {
  value: number
  onChange?: (value: number) => void
  readonly?: boolean
}

export function StarRating({ value, onChange, readonly = false }: StarRatingProps) {
  return (
    <div className="flex gap-1" role="group" aria-label="Vlerësim">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          onClick={() => onChange?.(star)}
          className={cn(
            'flex h-11 w-11 items-center justify-center border border-border font-mono text-sm transition-colors rounded-none',
            !readonly && 'hover:border-sienna cursor-pointer',
            readonly && 'cursor-default',
            star <= value ? 'bg-sienna text-cream border-sienna' : 'bg-paper text-ink',
          )}
          aria-label={`${star} star${star > 1 ? 's' : ''}`}
        >
          ★
        </button>
      ))}
    </div>
  )
}
