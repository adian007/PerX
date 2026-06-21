import { NavLink } from 'react-router-dom'
import { t } from '@/i18n'
import { cn } from '@/lib/utils'

const NAV_LINKS = [
  { to: '/employee', labelKey: 'nav.home', end: true },
  { to: '/employee/packages', labelKey: 'nav.packages' },
  { to: '/employee/selections', labelKey: 'nav.selections' },
  { to: '/employee/journey', labelKey: 'nav.journey' },
  { to: '/employee/explore', labelKey: 'nav.explore' },
  { to: '/employee/saved', labelKey: 'nav.saved' },
  { to: '/employee/vision', labelKey: 'nav.vision' },
] as const

export function EmployeeNav() {
  return (
    <nav
      aria-label="Navigimi i punonjësit"
      className="border-b border-ink/10 bg-paper/50"
    >
      <div className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-6 py-2 scrollbar-none">
        {NAV_LINKS.map(({ to, labelKey, ...rest }) => (
          <NavLink
            key={to}
            to={to}
            end={'end' in rest ? rest.end : false}
            className={({ isActive }) =>
              cn(
                'shrink-0 px-4 py-2 font-sans text-sm transition-colors',
                isActive
                  ? 'bg-ink text-cream'
                  : 'text-muted hover:bg-paper hover:text-ink',
              )
            }
          >
            {t(labelKey)}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
