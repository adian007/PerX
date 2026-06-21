import { LANDING_SECTIONS, type LandingSectionId } from '@/components/landing/landingMotion'

interface LandingMobileNavProps {
  activeId: LandingSectionId
  onNavigate: (id: LandingSectionId) => void
}

export function LandingMobileNav({ activeId, onNavigate }: LandingMobileNavProps) {
  const activeIndex = LANDING_SECTIONS.findIndex((s) => s.id === activeId)

  return (
    <nav
      aria-label="Seksionet e faqes kryesore"
      className="fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 items-center gap-2 border border-border bg-cream px-4 py-2 md:hidden"
    >
      {LANDING_SECTIONS.map(({ id, step }, i) => {
        const isActive = activeId === id
        const isPast = i < activeIndex
        return (
          <button
            key={id}
            type="button"
            onClick={() => onNavigate(id)}
            aria-label={`Section ${step}`}
            aria-current={isActive ? 'true' : undefined}
            className={`font-mono text-[10px] tabular-nums transition-colors ${
              isActive
                ? 'text-sienna'
                : isPast
                  ? 'text-ink/60'
                  : 'text-muted'
            }`}
          >
            {step}
          </button>
        )
      })}
    </nav>
  )
}
