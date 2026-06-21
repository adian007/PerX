import { t } from '@/i18n'

interface BudgetRingProps {
  allocated: number
  spent: number
  pending: number
  size?: number
  currencyCode?: string
  formatAmount?: (cents: number) => string
}

export function BudgetRing({
  allocated,
  spent,
  pending,
  size = 160,
  formatAmount = (cents) => `${(cents / 100).toFixed(0)}`,
}: BudgetRingProps) {
  const used = spent + pending
  const pct = allocated > 0 ? Math.min(100, (used / allocated) * 100) : 0
  const radius = (size - 16) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-4">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(26,26,26,0.12)"
          strokeWidth="8"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#8B4513"
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="butt"
        />
      </svg>
      <div className="text-center">
        <p className="font-mono text-2xl tabular-nums">{pct.toFixed(0)}%</p>
        <p className="text-sm text-muted">{t('budgetRing.utilized')}</p>
        <p className="mt-2 font-mono text-xs tabular-nums">
          {formatAmount(spent)} {t('budgetRing.spent')} · {formatAmount(pending)}{' '}
          {t('budgetRing.pending')} · {formatAmount(Math.max(0, allocated - used))}{' '}
          {t('budgetRing.remaining')}
        </p>
      </div>
    </div>
  )
}
