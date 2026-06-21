import { useCallback, useMemo, useRef, type RefObject } from 'react'
import { useReducedMotion } from 'framer-motion'
import { PublicNav } from '@/components/layout/PublicNav'
import { LandingHeroSection } from '@/components/landing/LandingHeroSection'
import { LandingEcosystemSection } from '@/components/landing/LandingEcosystemSection'
import { LandingPartnersSection } from '@/components/landing/LandingPartnersSection'
import { LandingOriginSection } from '@/components/landing/LandingOriginSection'
import { LandingSectionNav } from '@/components/landing/LandingSectionNav'
import { LandingMobileNav } from '@/components/landing/LandingMobileNav'
import { LANDING_SECTIONS, type LandingSectionId } from '@/components/landing/landingMotion'
import { useActiveSection } from '@/hooks/useActiveSection'

export function LandingPage() {
  const reducedMotion = useReducedMotion()
  const sectionIds = useMemo(() => LANDING_SECTIONS.map((s) => s.id), [])
  const activeId = useActiveSection(sectionIds)

  const heroRef = useRef<HTMLElement>(null)
  const ecosystemRef = useRef<HTMLElement>(null)
  const partnersRef = useRef<HTMLElement>(null)
  const originRef = useRef<HTMLElement>(null)

  const sectionRefs: Record<LandingSectionId, RefObject<HTMLElement | null>> = useMemo(
    () => ({
      vision: heroRef,
      ecosystem: ecosystemRef,
      network: partnersRef,
      origin: originRef,
    }),
    [],
  )

  const scrollToSection = useCallback(
    (id: LandingSectionId) => {
      sectionRefs[id].current?.scrollIntoView({
        behavior: reducedMotion ? 'auto' : 'smooth',
        block: 'start',
      })
    },
    [reducedMotion, sectionRefs],
  )

  return (
    <div className="landing-scroll h-screen snap-y snap-mandatory overflow-y-scroll scroll-smooth bg-cream">
      <PublicNav />

      <LandingSectionNav activeId={activeId} onNavigate={scrollToSection} />
      <LandingMobileNav activeId={activeId} onNavigate={scrollToSection} />

      <LandingHeroSection
        ref={heroRef}
        reducedMotion={reducedMotion}
        onScrollNext={() => scrollToSection('ecosystem')}
      />

      <LandingEcosystemSection
        ref={ecosystemRef}
        reducedMotion={reducedMotion}
        onScrollNext={() => scrollToSection('network')}
      />

      <LandingPartnersSection
        ref={partnersRef}
        reducedMotion={reducedMotion}
        onScrollNext={() => scrollToSection('origin')}
      />

      <LandingOriginSection ref={originRef} reducedMotion={reducedMotion} />
    </div>
  )
}
