import { forwardRef } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { HeroVisual } from '@/components/editorial/HeroVisual'
import { ScrollHint } from '@/components/landing/ScrollHint'
import { t } from '@/i18n'

interface LandingHeroSectionProps {
  reducedMotion: boolean | null
  onScrollNext: () => void
}

export const LandingHeroSection = forwardRef<HTMLElement, LandingHeroSectionProps>(
  function LandingHeroSection({ reducedMotion, onScrollNext }, ref) {
    return (
      <section
        ref={ref}
        id="vision"
        className="relative flex min-h-screen snap-start snap-always flex-col justify-center border-b border-[#1A1A1A]/12 px-6 py-12 pb-32 md:py-16 md:pb-28"
      >
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="space-y-8 lg:space-y-10">
            <motion.p
              initial={reducedMotion ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="font-mono text-xs uppercase tracking-[0.3em] text-sienna md:text-sm"
            >
              01 · {t('landing.sectionVision')}
            </motion.p>
            <motion.h1
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="font-display text-5xl font-bold italic leading-[0.95] md:text-6xl lg:text-7xl xl:text-[5.5rem]"
            >
              {t('landing.heroTitle')}
            </motion.h1>
            <motion.p
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="max-w-xl text-lg leading-relaxed text-muted md:text-xl"
            >
              {t('landing.heroBody')}
            </motion.p>

            <motion.div
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex flex-wrap gap-3"
            >
              <Button asChild size="lg">
                <Link to="/login?mode=register">{t('landing.getStarted')}</Link>
              </Button>
              <Button type="button" variant="outline" size="lg" onClick={onScrollNext}>
                {t('landing.seeHowItWorks')}
              </Button>
            </motion.div>

            <motion.div
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="grid grid-cols-3 gap-4 border-t border-[#1A1A1A]/12 pt-8"
            >
              {[
                { value: '50+', label: t('landing.statPerks') },
                { value: '+75', label: t('landing.statPts') },
                { value: 'AI', label: t('landing.statAi') },
              ].map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={reducedMotion ? false : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + i * 0.08 }}
                >
                  <p className="font-mono text-2xl tabular-nums text-ink md:text-3xl">
                    {stat.value}
                  </p>
                  <p className="mt-1 text-xs uppercase tracking-wide text-muted md:text-sm">
                    {stat.label}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          </div>

          <motion.div
            initial={reducedMotion ? false : { opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.25, duration: 0.6 }}
            className="hidden lg:block"
          >
            <HeroVisual />
          </motion.div>
        </div>

        <motion.div
          initial={reducedMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mx-auto mt-10 w-full max-w-sm lg:hidden"
        >
          <HeroVisual />
        </motion.div>

        <ScrollHint
          onClick={onScrollNext}
          nextLabel={`02 · ${t('landing.sectionEcosystem')}`}
        />
      </section>
    )
  },
)
