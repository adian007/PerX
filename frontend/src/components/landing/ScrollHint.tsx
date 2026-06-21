import { ChevronDown } from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'
import { t } from '@/i18n'

interface ScrollHintProps {
  onClick: () => void
  nextLabel?: string
}

export function ScrollHint({ onClick, nextLabel }: ScrollHintProps) {
  const reducedMotion = useReducedMotion()

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={nextLabel ? `Lëviz te ${nextLabel}` : 'Lëviz te seksioni tjetër'}
      className="group absolute bottom-20 left-1/2 z-30 flex -translate-x-1/2 flex-col items-center gap-1.5 text-xs uppercase tracking-widest text-muted transition-colors hover:text-ink md:bottom-10"
    >
      {nextLabel && (
        <span className="font-mono text-[10px] tracking-[0.25em] opacity-70">{nextLabel}</span>
      )}
      <motion.span
        animate={reducedMotion ? undefined : { y: [0, 4, 0] }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 2.2, repeat: Infinity, ease: 'easeInOut' }
        }
        className="flex flex-col items-center gap-1"
      >
        <span>{t('common.scroll')}</span>
        <ChevronDown className="size-4" strokeWidth={1.5} aria-hidden />
      </motion.span>
    </button>
  )
}
