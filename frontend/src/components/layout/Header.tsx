import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { levelLabel, t } from '@/i18n'
import { useAuthStore } from '@/stores/authStore'
import { useUserState } from '@/stores/userState'
import { formatPoints } from '@/lib/utils'

export function Header() {
  const navigate = useNavigate()
  const { logout } = useAuthStore()
  const { level, streakDays, pointsBalance, reset } = useUserState()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-[#1A1A1A]/12 bg-cream">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link to="/employee" className="font-display text-2xl font-semibold italic text-ink">
          PerX
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="outline">
            {t('header.level')}{level} · {levelLabel(level)}
          </Badge>
          <Badge variant="outline">
            {streakDays} {t('header.streak')}
          </Badge>
          <Badge variant="default">
            {formatPoints(pointsBalance)} {t('common.points')}
          </Badge>
          {import.meta.env.DEV && (
            <Button variant="ghost" size="sm" onClick={() => void reset()}>
              {t('common.reset')}
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            {t('common.signOut')}
          </Button>
        </div>
      </div>
    </header>
  )
}
