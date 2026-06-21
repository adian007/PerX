import { forwardRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ScrollHint } from '@/components/landing/ScrollHint'
import { EcosystemFlowVisual } from '@/components/landing/visuals/EcosystemFlowVisual'
import { t } from '@/i18n'
import {
  fadeUp,
  sectionInitial,
  sectionViewport,
  slideFromLeft,
  slideFromRight,
  stagger,
} from '@/components/landing/landingMotion'

interface LandingEcosystemSectionProps {
  reducedMotion: boolean | null
  onScrollNext: () => void
}

export const LandingEcosystemSection = forwardRef<HTMLElement, LandingEcosystemSectionProps>(
  function LandingEcosystemSection({ reducedMotion, onScrollNext }, ref) {
    const [activeStep, setActiveStep] = useState(0)

    const steps = [
      { step: 'A', title: t('landing.stepDiscover'), body: t('landing.stepDiscoverBody') },
      { step: 'B', title: t('landing.stepApprove'), body: t('landing.stepApproveBody') },
      { step: 'C', title: t('landing.stepDeliver'), body: t('landing.stepDeliverBody') },
    ]

    useEffect(() => {
      if (reducedMotion) return
      const timer = window.setInterval(() => {
        setActiveStep((prev) => (prev + 1) % steps.length)
      }, 4000)
      return () => window.clearInterval(timer)
    }, [reducedMotion, steps.length])

    return (
      <motion.section
        ref={ref}
        id="ecosystem"
        initial={sectionInitial(reducedMotion)}
        whileInView="visible"
        viewport={sectionViewport(reducedMotion)}
        variants={stagger}
        className="relative flex min-h-screen snap-start snap-always flex-col justify-start border-t border-[#1A1A1A]/12 bg-paper px-6 py-16 pb-32 md:py-20 md:pb-28"
      >
        <div className="mx-auto grid w-full max-w-6xl items-start gap-10 lg:grid-cols-[minmax(0,28rem)_1fr] lg:gap-12 xl:gap-16">
          <motion.div variants={slideFromLeft} className="order-2 lg:sticky lg:top-24 lg:order-1">
            <EcosystemFlowVisual />
          </motion.div>

          <div className="order-1 space-y-10 lg:order-2">
            <motion.div variants={fadeUp} className="space-y-5">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-sienna md:text-sm">
                02 · {t('landing.sectionEcosystem')}
              </p>
              <h2 className="font-display text-5xl font-semibold md:text-6xl lg:text-7xl">
                {t('landing.ecosystemTitle')}
              </h2>
              <p className="max-w-xl text-lg text-muted md:text-xl">{t('landing.ecosystemBody')}</p>
              <p className="max-w-xl border-l-2 border-sienna pl-4 text-base leading-relaxed text-muted md:text-lg">
                {t('landing.ecosystemOpportunity')}
              </p>
            </motion.div>

            <motion.div variants={stagger} className="space-y-3">
              {steps.map((item, i) => {
                const isActive = i === activeStep
                return (
                  <motion.div
                    key={item.title}
                    variants={slideFromRight}
                    animate={{
                      borderColor: isActive ? 'rgba(139,69,19,0.5)' : 'rgba(26,26,26,0.12)',
                      backgroundColor: isActive ? '#FAF9F5' : 'transparent',
                    }}
                    transition={{ duration: 0.4 }}
                    className="border border-[#1A1A1A]/12 p-5 md:p-6"
                  >
                    <div className="flex items-start gap-4">
                      <span
                        className={`flex size-8 shrink-0 items-center justify-center border font-mono text-sm transition-colors ${
                          isActive
                            ? 'border-sienna bg-sienna/10 text-sienna'
                            : 'border-[#1A1A1A]/12 text-muted'
                        }`}
                      >
                        {item.step}
                      </span>
                      <div>
                        <h3 className="font-display text-xl font-semibold md:text-2xl">
                          {item.title}
                        </h3>
                        <p className="mt-2 text-base leading-relaxed text-muted">{item.body}</p>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>
          </div>
        </div>

        <ScrollHint
          onClick={onScrollNext}
          nextLabel={`03 · ${t('landing.sectionNetwork')}`}
        />
      </motion.section>
    )
  },
)
