import { forwardRef } from 'react'
import { motion } from 'framer-motion'
import { ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ChallengeOriginVisual } from '@/components/landing/visuals/ChallengeOriginVisual'
import { t } from '@/i18n'
import {
  fadeUp,
  sectionInitial,
  sectionViewport,
  slideFromRight,
  stagger,
} from '@/components/landing/landingMotion'

interface LandingOriginSectionProps {
  reducedMotion: boolean | null
}

export const LandingOriginSection = forwardRef<HTMLElement, LandingOriginSectionProps>(
  function LandingOriginSection({ reducedMotion }, ref) {
    const stats = [
      { value: '3.1M+', label: t('landing.originStatCustomers') },
      { value: '6,000', label: t('landing.originStatEmployees') },
      { value: 'AI', label: t('landing.originStatAi') },
    ]

    return (
      <motion.section
        ref={ref}
        id="origin"
        initial={sectionInitial(reducedMotion)}
        whileInView="visible"
        viewport={sectionViewport(reducedMotion)}
        variants={stagger}
        className="relative flex min-h-screen snap-start snap-always flex-col justify-start border-t border-[#1A1A1A]/12 bg-paper px-6 py-16 pb-24 md:py-20 md:pb-24"
      >
        <div className="mx-auto grid w-full max-w-6xl items-start gap-10 lg:grid-cols-2 lg:gap-12 xl:gap-16">
          <div className="space-y-10">
            <motion.div variants={fadeUp} className="space-y-5">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-sienna md:text-sm">
                04 · {t('landing.sectionOrigin')}
              </p>
              <h2 className="font-display text-5xl font-semibold md:text-6xl lg:text-7xl">
                {t('landing.originTitle')}
              </h2>
              <p className="max-w-xl text-lg leading-relaxed text-muted md:text-xl">
                {t('landing.originBody')}
              </p>
            </motion.div>

            <motion.div
              variants={fadeUp}
              className="grid gap-6 border border-[#1A1A1A]/12 bg-cream p-8 md:grid-cols-3 md:p-10"
            >
              {stats.map((stat) => (
                <div key={stat.label} className="text-center md:text-left">
                  <p className="font-mono text-3xl tabular-nums text-ink md:text-4xl">
                    {stat.value}
                  </p>
                  <p className="mt-2 text-sm uppercase tracking-wide text-muted">{stat.label}</p>
                </div>
              ))}
            </motion.div>

            <motion.div variants={fadeUp} className="space-y-6">
              <Button asChild variant="outline" size="lg">
                <a
                  href="https://www.teamsystem.com/en/"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${t('landing.learnTeamSystem')} (hapet në skedë të re)`}
                >
                  {t('landing.learnTeamSystem')}
                  <ExternalLink className="size-4" strokeWidth={1.5} aria-hidden />
                </a>
              </Button>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
                {t('landing.demoPrototype')}
              </p>
            </motion.div>
          </div>

          <motion.div variants={slideFromRight}>
            <ChallengeOriginVisual />
          </motion.div>
        </div>
      </motion.section>
    )
  },
)
