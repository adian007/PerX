import { useEffect, useState } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Dumbbell, Heart, Shield, UtensilsCrossed } from 'lucide-react'
import { MOCK_PARTNERS, PARTNER_CATEGORIES } from '@/data/mockPartners'

const CATEGORY_ICONS = {
  fitness: Dumbbell,
  food: UtensilsCrossed,
  wellness: Heart,
  insurance: Shield,
} as const

export function PartnersOrbitVisual() {
  const reducedMotion = useReducedMotion()
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (reducedMotion) return
    const timer = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % MOCK_PARTNERS.length)
    }, 3200)
    return () => window.clearInterval(timer)
  }, [reducedMotion])

  const activePartner = MOCK_PARTNERS[activeIndex]
  const ActiveIcon = CATEGORY_ICONS[activePartner.category]

  return (
    <div
      className="relative mx-auto w-full max-w-[16rem] sm:max-w-xs lg:mx-0"
      aria-hidden
    >
      <div className="border border-[#1A1A1A]/10 bg-cream/50 p-3 sm:p-4">
        <div className="relative aspect-square w-full">
          <motion.svg
            viewBox="0 0 320 320"
            className="h-full w-full"
            animate={reducedMotion ? undefined : { rotate: 360 }}
            transition={
              reducedMotion
                ? undefined
                : { duration: 120, repeat: Infinity, ease: 'linear' }
            }
          >
            <circle
              cx="160"
              cy="160"
              r="110"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.5"
              opacity="0.2"
            />
            {MOCK_PARTNERS.map((partner, i) => {
              const angle = (i / MOCK_PARTNERS.length) * 360 - 90
              const rad = (angle * Math.PI) / 180
              const x = 160 + 110 * Math.cos(rad)
              const y = 160 + 110 * Math.sin(rad)
              const isActive = i === activeIndex
              return (
                <g key={partner.id}>
                  <line
                    x1="160"
                    y1="160"
                    x2={x}
                    y2={y}
                    stroke="currentColor"
                    strokeWidth="0.5"
                    opacity={isActive ? 0.5 : 0.15}
                    strokeDasharray="4 4"
                  />
                  <circle
                    cx={x}
                    cy={y}
                    r={isActive ? 8 : 5}
                    fill={isActive ? '#8B4513' : '#F4F1EA'}
                    stroke="currentColor"
                    strokeWidth="1"
                  />
                </g>
              )
            })}
            <circle
              cx="160"
              cy="160"
              r="28"
              fill="#FAF9F5"
              stroke="#8B4513"
              strokeWidth="1.5"
            />
            <text
              x="160"
              y="158"
              textAnchor="middle"
              className="fill-ink font-sans text-[9px] uppercase tracking-widest"
            >
              Tirana
            </text>
            <text
              x="160"
              y="172"
              textAnchor="middle"
              className="fill-[#1A1A1A]/55 font-sans text-[8px] uppercase"
            >
              Network
            </text>
          </motion.svg>

          <div className="absolute left-1/2 top-2 flex -translate-x-1/2 gap-1.5">
            {MOCK_PARTNERS.map((partner, i) => (
              <motion.span
                key={partner.id}
                className="h-1 w-4 bg-[#1A1A1A]/15"
                animate={{
                  backgroundColor: i === activeIndex ? '#8B4513' : 'rgba(26,26,26,0.15)',
                }}
                transition={{ duration: 0.3 }}
              />
            ))}
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activePartner.id}
            initial={reducedMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reducedMotion ? undefined : { opacity: 0, y: -8 }}
            transition={{ duration: 0.45, ease: [0.25, 0.1, 0.25, 1] }}
            className="mt-3 border border-[#1A1A1A]/12 bg-paper p-3"
          >
            <div className="flex items-start gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center border border-[#1A1A1A]/12 bg-cream">
                <ActiveIcon className="size-3.5 text-sienna" strokeWidth={1.5} />
              </div>
              <div className="min-w-0">
                <p className="font-mono text-[10px] uppercase tracking-widest text-sienna">
                  {PARTNER_CATEGORIES[activePartner.category]}
                </p>
                <p className="mt-0.5 truncate font-display text-base font-semibold">
                  {activePartner.name}
                </p>
                <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">
                  {activePartner.perkOffer}
                </p>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
