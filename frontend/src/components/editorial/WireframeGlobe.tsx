import { motion, useReducedMotion } from 'framer-motion'

export function WireframeGlobe() {
  const reducedMotion = useReducedMotion()

  return (
    <div className="pointer-events-none absolute right-0 top-0 h-64 w-64 opacity-[0.08] md:h-80 md:w-80" aria-hidden>
      <motion.svg
        viewBox="0 0 200 200"
        className="h-full w-full text-ink"
        animate={reducedMotion ? undefined : { rotate: 360 }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 25, repeat: Infinity, ease: 'linear' }
        }
        aria-hidden
      >
        <circle cx="100" cy="100" r="90" fill="none" stroke="currentColor" strokeWidth="0.5" />
        <ellipse cx="100" cy="100" rx="90" ry="30" fill="none" stroke="currentColor" strokeWidth="0.5" />
        <ellipse cx="100" cy="100" rx="90" ry="60" fill="none" stroke="currentColor" strokeWidth="0.5" />
        <ellipse cx="100" cy="100" rx="30" ry="90" fill="none" stroke="currentColor" strokeWidth="0.5" />
        <ellipse cx="100" cy="100" rx="60" ry="90" fill="none" stroke="currentColor" strokeWidth="0.5" />
        <line x1="10" y1="100" x2="190" y2="100" stroke="currentColor" strokeWidth="0.5" />
        <line x1="100" y1="10" x2="100" y2="190" stroke="currentColor" strokeWidth="0.5" />
        {[0, 30, 60, 90, 120, 150].map((lat) => (
          <ellipse
            key={lat}
            cx="100"
            cy="100"
            rx={90 * Math.cos((lat * Math.PI) / 180)}
            ry="90"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.3"
            transform={`rotate(${lat} 100 100)`}
          />
        ))}
      </motion.svg>
    </div>
  )
}
