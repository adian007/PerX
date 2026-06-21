import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { ACHIEVEMENTS } from '@/data/mockAchievements'
import { t } from '@/i18n'
import { useUserState } from '@/stores/userState'
import { cn } from '@/lib/utils'

export function AchievementsPage() {
  const { unlockedAchievements, unlockedAtBySlug, marathonerMiles, setMarathonerMiles, wishlistIds } =
    useUserState()

  const achievements = useMemo(
    () =>
      ACHIEVEMENTS.map((a) => ({
        ...a,
        unlocked: unlockedAchievements.includes(a.slug),
        unlockedAt: unlockedAtBySlug[a.slug] ?? a.unlockedAt,
        progress:
          a.slug === 'marathoner'
            ? marathonerMiles
            : a.slug === 'wishlist-curator'
              ? wishlistIds.length
              : a.progress,
      })),
    [unlockedAchievements, unlockedAtBySlug, marathonerMiles, wishlistIds.length],
  )

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold">{t('achievements.title')}</h1>
        <p className="mt-2 text-muted">{t('achievements.body')}</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {achievements.map((achievement) => (
          <Card
            key={achievement.slug}
            className={cn(
              !achievement.unlocked && !achievement.interactive && 'opacity-40',
              !achievement.unlocked && !achievement.interactive && 'border-dashed',
              achievement.unlocked && 'border-l-4 border-l-sienna',
            )}
          >
            <CardHeader>
              <CardTitle className="text-lg">{achievement.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted">{achievement.description}</p>
              {achievement.unlocked ? (
                <p className="font-mono text-xs tabular-nums text-sienna">
                  {t('achievements.unlocked')}{' '}
                  {achievement.unlockedAt
                    ? achievement.unlockedAt.slice(0, 10)
                    : t('achievements.recently')}
                </p>
              ) : achievement.interactive && achievement.slug === 'marathoner' ? (
                <div className="space-y-3">
                  <p className="text-xs text-muted">{achievement.requirement}</p>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      max={200}
                      value={marathonerMiles || ''}
                      onChange={(e) => void setMarathonerMiles(Number(e.target.value) || 0)}
                      placeholder={t('achievements.miles')}
                      className="max-w-[120px] font-mono tabular-nums"
                    />
                    <span className="font-mono text-sm tabular-nums">
                      / {achievement.goal} km
                    </span>
                  </div>
                  <motion.div initial={false} animate={{ opacity: 1 }}>
                    <Progress
                      value={Math.min(
                        100,
                        ((marathonerMiles ?? 0) / (achievement.goal ?? 100)) * 100,
                      )}
                    />
                  </motion.div>
                </div>
              ) : (
                <p className="text-xs text-muted">{achievement.requirement}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
