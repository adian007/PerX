import { forwardRef } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { PartnerCard } from '@/components/editorial/PartnerCard'
import { ScrollHint } from '@/components/landing/ScrollHint'
import { PartnersOrbitVisual } from '@/components/landing/visuals/PartnersOrbitVisual'
import { MOCK_PARTNERS } from '@/data/mockPartners'
import { t } from '@/i18n'
import {
  fadeUp,
  sectionInitial,
  sectionViewport,
  scaleIn,
  stagger,
} from '@/components/landing/landingMotion'

interface LandingPartnersSectionProps {
  reducedMotion: boolean | null
  onScrollNext: () => void
}

export const LandingPartnersSection = forwardRef<HTMLElement, LandingPartnersSectionProps>(
  function LandingPartnersSection({ reducedMotion, onScrollNext }, ref) {
    return (
      <motion.section
        ref={ref}
        id="network"
        initial={sectionInitial(reducedMotion)}
        whileInView="visible"
        viewport={sectionViewport(reducedMotion)}
        variants={stagger}
        className="relative flex min-h-screen snap-start snap-always flex-col justify-start border-t border-[#1A1A1A]/12 px-6 py-16 pb-32 md:py-20 md:pb-28"
      >
        <div className="mx-auto max-w-6xl space-y-12 md:space-y-14">
          <div className="grid items-start gap-8 lg:grid-cols-[1fr_minmax(0,16rem)] lg:gap-12 xl:grid-cols-[1fr_minmax(0,18rem)] xl:gap-16">
            <motion.div variants={fadeUp} className="space-y-5">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-sienna md:text-sm">
                03 · {t('landing.sectionNetwork')}
              </p>
              <h2 className="font-display text-5xl font-semibold md:text-6xl lg:text-7xl">
                {t('landing.partnersTitle')}
              </h2>
              <p className="max-w-2xl text-lg text-muted md:text-xl">
                {t('landing.partnersBody')}
              </p>
            </motion.div>

            <motion.div variants={scaleIn} className="hidden lg:sticky lg:top-24 lg:block">
              <PartnersOrbitVisual />
            </motion.div>
          </div>

          <motion.div variants={scaleIn} className="lg:hidden">
            <PartnersOrbitVisual />
          </motion.div>

          <motion.div variants={stagger} className="grid gap-6 md:grid-cols-2 md:gap-8">
            {MOCK_PARTNERS.map((partner, i) => (
              <motion.div
                key={partner.id}
                variants={fadeUp}
                whileHover={reducedMotion ? undefined : { y: -4 }}
                transition={{ duration: 0.25 }}
                style={{ transitionDelay: `${i * 0.05}s` }}
              >
                <PartnerCard partner={partner} />
              </motion.div>
            ))}
          </motion.div>

          <motion.div
            variants={fadeUp}
            className="grid gap-6 border border-[#1A1A1A]/12 bg-paper p-8 md:grid-cols-3 md:p-10"
          >
            {[
              { value: '4', label: t('landing.statCategories') },
              { value: '17+', label: t('landing.statLocations') },
              { value: '100%', label: t('landing.statApproved') },
            ].map((stat) => (
              <div key={stat.label} className="text-center md:text-left">
                <p className="font-mono text-3xl tabular-nums text-ink md:text-4xl">{stat.value}</p>
                <p className="mt-2 text-sm uppercase tracking-wide text-muted">{stat.label}</p>
              </div>
            ))}
          </motion.div>

          <motion.div variants={fadeUp} className="space-y-6 pb-2 text-center">
            <p className="mx-auto max-w-2xl text-base text-muted md:text-lg">
              {t('landing.partnerJoinBody')}
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Button asChild size="lg">
                <Link to="/login?mode=register">{t('landing.becomePartner')}</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/login">{t('landing.employerSignIn')}</Link>
              </Button>
            </div>
          </motion.div>
        </div>

        <ScrollHint
          onClick={onScrollNext}
          nextLabel={`04 · ${t('landing.sectionOrigin')}`}
        />
      </motion.section>
    )
  },
)
