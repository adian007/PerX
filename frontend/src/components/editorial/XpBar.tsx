import { Progress } from '@/components/ui/progress'
import { levelLabel, t } from '@/i18n'
import { useUserState } from '@/stores/userState'

export function XpBar() {
  const { xp, xpToNextLevel, level } = useUserState()
  const pct = Math.min(100, (xp / xpToNextLevel) * 100)

  return (
    <div className="space-y-2">
      <Progress value={pct} className="h-4" />
      <div className="flex flex-wrap items-baseline justify-between gap-2 font-mono text-sm tabular-nums">
        <span>
          {xp} / {xpToNextLevel} XP
        </span>
        <span className="text-muted">
          {t('header.level')}{level} · {levelLabel(level)}
        </span>
      </div>
    </div>
  )
}
