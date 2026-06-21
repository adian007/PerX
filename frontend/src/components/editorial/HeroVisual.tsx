import { motion, useReducedMotion } from 'framer-motion'

const ORBIT_NODES = [
  { label: 'Mirëqenie', angle: 0 },
  { label: 'Udhëtim', angle: 72 },
  { label: 'Mësim', angle: 144 },
  { label: 'Familje', angle: 216 },
  { label: 'Financë', angle: 288 },
]

export function HeroVisual() {
  const reducedMotion = useReducedMotion()

  return (
    <div
      className="relative mx-auto flex aspect-square w-full max-w-lg items-center justify-center lg:max-w-none"
      aria-hidden
    >
      {/* Soft gradient wash */}
      <div className="absolute inset-8 bg-gradient-to-br from-sienna/8 via-transparent to-[#1A1A1A]/5" />

      {/* Decorative frame */}
      <div className="absolute inset-4 border border-[#1A1A1A]/10" />
      <div className="absolute inset-8 border border-[#1A1A1A]/6" />

      {/* Central orbit diagram */}
      <motion.svg
        viewBox="0 0 400 400"
        className="relative h-full w-full text-ink"
        animate={reducedMotion ? undefined : { rotate: 360 }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 90, repeat: Infinity, ease: 'linear' }
        }
      >
        <circle cx="200" cy="200" r="140" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.25" />
        <circle cx="200" cy="200" r="100" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.35" />
        <circle cx="200" cy="200" r="60" fill="none" stroke="currentColor" strokeWidth="0.75" opacity="0.5" />

        {[0, 45, 90, 135].map((deg) => (
          <line
            key={deg}
            x1="200"
            y1="200"
            x2={200 + 140 * Math.cos((deg * Math.PI) / 180)}
            y2={200 + 140 * Math.sin((deg * Math.PI) / 180)}
            stroke="currentColor"
            strokeWidth="0.4"
            opacity="0.2"
          />
        ))}

        {/* Wireframe globe core */}
        <g transform="translate(200, 200)">
          <circle r="45" fill="none" stroke="currentColor" strokeWidth="0.75" />
          <ellipse rx="45" ry="15" fill="none" stroke="currentColor" strokeWidth="0.5" />
          <ellipse rx="45" ry="30" fill="none" stroke="currentColor" strokeWidth="0.5" />
          <ellipse rx="15" ry="45" fill="none" stroke="currentColor" strokeWidth="0.5" />
          <ellipse rx="30" ry="45" fill="none" stroke="currentColor" strokeWidth="0.5" />
        </g>

        {ORBIT_NODES.map(({ angle }) => {
          const rad = (angle * Math.PI) / 180
          const x = 200 + 140 * Math.cos(rad)
          const y = 200 + 140 * Math.sin(rad)
          return (
            <g key={angle}>
              <line
                x1="200"
                y1="200"
                x2={x}
                y2={y}
                stroke="currentColor"
                strokeWidth="0.5"
                opacity="0.3"
                strokeDasharray="4 4"
              />
              <circle cx={x} cy={y} r="6" fill="#F4F1EA" stroke="currentColor" strokeWidth="1" />
              <circle cx={x} cy={y} r="2.5" fill="#8B4513" />
            </g>
          )
        })}
      </motion.svg>

      {/* Counter-rotating labels (stay readable) */}
      <motion.div
        className="absolute inset-0"
        animate={reducedMotion ? undefined : { rotate: -360 }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 90, repeat: Infinity, ease: 'linear' }
        }
      >
        {ORBIT_NODES.map(({ label, angle }) => {
          const rad = (angle * Math.PI) / 180
          const x = 50 + 35 * Math.cos(rad)
          const y = 50 + 35 * Math.sin(rad)
          return (
            <span
              key={label}
              className="absolute -translate-x-1/2 -translate-y-1/2 border border-[#1A1A1A]/12 bg-paper px-2 py-1 font-sans text-[10px] uppercase tracking-widest text-muted md:text-xs"
              style={{ left: `${x}%`, top: `${y}%` }}
            >
              {label}
            </span>
          )
        })}
      </motion.div>

      {/* Floating stat chips */}
      <motion.div
        className="absolute left-0 top-1/4 border border-[#1A1A1A]/12 bg-paper px-3 py-2"
        animate={reducedMotion ? undefined : { y: [0, -6, 0] }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 5, repeat: Infinity, ease: 'easeInOut' }
        }
      >
        <p className="font-mono text-xs tabular-nums text-sienna">+75 pikë</p>
        <p className="text-[10px] uppercase tracking-wide text-muted">Për përfitim</p>
      </motion.div>

      <motion.div
        className="absolute bottom-1/4 right-0 border border-[#1A1A1A]/12 bg-paper px-3 py-2"
        animate={reducedMotion ? undefined : { y: [0, 6, 0] }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }
        }
      >
        <p className="font-mono text-xs tabular-nums text-sienna">AI</p>
        <p className="text-[10px] uppercase tracking-wide text-muted">Këshilltar</p>
      </motion.div>
    </div>
  )
}
