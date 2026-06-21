import { NavLink, useMatch } from 'react-router-dom'
import { Home, Map, Compass, Package, ClipboardList, Heart, ScanEye, type LucideIcon } from 'lucide-react'
import { t } from '@/i18n'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/employee', labelKey: 'nav.home', icon: Home, end: true },
  { to: '/employee/packages', labelKey: 'nav.packages', icon: Package },
  { to: '/employee/selections', labelKey: 'nav.status', icon: ClipboardList },
  { to: '/employee/explore', labelKey: 'nav.explore', icon: Compass },
  { to: '/employee/vision', labelKey: 'nav.vision', icon: ScanEye },
  { to: '/employee/journey', labelKey: 'nav.journey', icon: Map },
  { to: '/employee/saved', labelKey: 'nav.saved', icon: Heart },
] as const

function BottomNavItem({
  to,
  labelKey,
  icon: Icon,
  end,
}: {
  to: string
  labelKey: string
  icon: LucideIcon
  end?: boolean
}) {
  const match = useMatch({ path: to, end: end ?? false })

  return (
    <NavLink
      to={to}
      end={end}
      aria-current={match ? 'page' : undefined}
      className={({ isActive }) =>
        cn(
          'flex flex-1 flex-col items-center gap-1 py-3 font-sans text-xs transition-colors',
          isActive ? 'bg-ink text-cream' : 'text-ink hover:bg-paper',
        )
      }
    >
      <Icon className="h-5 w-5" aria-hidden />
      {t(labelKey)}
    </NavLink>
  )
}

export function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-[#1A1A1A]/12 bg-cream md:hidden">
      <div className="mx-auto flex max-w-6xl">
        {NAV_ITEMS.map(({ to, labelKey, icon, ...rest }) => (
          <BottomNavItem
            key={to}
            to={to}
            labelKey={labelKey}
            icon={icon}
            end={'end' in rest ? rest.end : undefined}
          />
        ))}
      </div>
    </nav>
  )
}
