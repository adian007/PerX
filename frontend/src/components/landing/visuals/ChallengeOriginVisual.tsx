import { motion, useReducedMotion } from 'framer-motion'
import { t } from '@/i18n'

const TIMELINE = [
  { year: '2026', labelKey: 'landing.originChallenge', detailKey: 'landing.originChallengeDetail' },
  { year: '→', labelKey: 'landing.originConceived', detailKey: 'landing.originConceivedDetail' },
  { year: 'Tani', labelKey: 'landing.originNow', detailKey: 'landing.originNowDetail' },
] as const

const MARKER_WIDTH = 'w-9 shrink-0 md:w-12'

export function ChallengeOriginVisual() {
  const reducedMotion = useReducedMotion()

  return (
    <div className="relative mx-auto w-full max-w-lg" aria-hidden>
      <div className="space-y-6 md:space-y-8">
        {TIMELINE.map(({ year, labelKey, detailKey }, i) => (
          <motion.div
            key={labelKey}
            className="flex gap-4 md:gap-6"
            initial={reducedMotion ? false : { opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ delay: i * 0.2, duration: 0.55, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <div className={`relative flex ${MARKER_WIDTH} flex-col items-center`}>
              {i < TIMELINE.length - 1 && (
                <div className="absolute top-9 bottom-0 left-1/2 w-px -translate-x-1/2 bg-[#1A1A1A]/15 md:top-12" />
              )}
              <div className="relative z-10 flex size-9 shrink-0 items-center justify-center border border-[#1A1A1A]/12 bg-cream md:size-12">
                <motion.div
                  className="size-2.5 bg-sienna md:size-3"
                  animate={
                    reducedMotion || i !== TIMELINE.length - 1
                      ? undefined
                      : { scale: [1, 1.4, 1], opacity: [1, 0.7, 1] }
                  }
                  transition={
                    reducedMotion
                      ? undefined
                      : { duration: 2.5, repeat: Infinity, ease: 'easeInOut' }
                  }
                />
              </div>
            </div>

            <div className="min-w-0 flex-1 border border-[#1A1A1A]/12 bg-paper p-5 md:p-6">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-mono text-sm tabular-nums text-sienna md:text-base">
                  {year}
                </span>
                <h3 className="font-display text-xl font-semibold md:text-2xl">{t(labelKey)}</h3>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted md:text-base">{t(detailKey)}</p>
            </div>
          </motion.div>
        ))}

        <motion.div
          className="flex gap-4 md:gap-6"
          initial={reducedMotion ? false : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.6, duration: 0.5 }}
        >
          <div className={MARKER_WIDTH} aria-hidden />
          <div className="flex min-w-0 flex-1 items-center justify-center gap-4 border border-[#1A1A1A]/12 bg-cream px-4 py-4 md:px-6">
            <span className="font-display text-2xl italic text-ink">PerX</span>
            <motion.span
              className="font-mono text-xs text-muted"
              animate={reducedMotion ? undefined : { opacity: [0.4, 1, 0.4] }}
              transition={
                reducedMotion
                  ? undefined
                  : { duration: 2, repeat: Infinity, ease: 'easeInOut' }
              }
            >
              ×
            </motion.span>
            <span className="font-display text-2xl italic text-ink">TeamSystem</span>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
