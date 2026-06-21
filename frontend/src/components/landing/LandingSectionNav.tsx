import { LANDING_SECTIONS, type LandingSectionId } from '@/components/landing/landingMotion'
import { t } from '@/i18n'

const SECTION_LABEL_KEYS: Record<LandingSectionId, string> = {
  vision: 'landing.sectionVision',
  ecosystem: 'landing.sectionEcosystem',
  network: 'landing.sectionNetwork',
  origin: 'landing.sectionOrigin',
}

interface LandingSectionNavProps {
  activeId: LandingSectionId
  onNavigate: (id: LandingSectionId) => void
}

export function LandingSectionNav({ activeId, onNavigate }: LandingSectionNavProps) {
  return (
    <nav
      aria-label="Seksionet e faqes kryesore"
      className="fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 flex-col gap-3 md:flex lg:right-8"
    >
      {LANDING_SECTIONS.map(({ id, step }) => {
        const label = t(SECTION_LABEL_KEYS[id])
        const isActive = activeId === id
        return (
          <button
            key={id}
            type="button"
            onClick={() => onNavigate(id)}
            aria-label={`Shko te ${label}`}
            aria-current={isActive ? 'true' : undefined}
            className="group flex items-center justify-end gap-3"
          >
            <span
              className={`font-mono text-[10px] uppercase tracking-widest transition-all duration-300 ${
                isActive
                  ? 'translate-x-0 opacity-100 text-ink'
                  : 'translate-x-2 opacity-0 group-hover:translate-x-0 group-hover:opacity-70 text-muted'
              }`}
            >
              {step} {label}
            </span>
            <span
              className={`block h-8 w-px transition-all duration-300 ${
                isActive ? 'bg-sienna scale-y-100' : 'bg-[#1A1A1A]/20 scale-y-50 group-hover:bg-[#1A1A1A]/40'
              }`}
            />
          </button>
        )
      })}
    </nav>
  )
}
