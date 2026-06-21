import { motion, useReducedMotion } from 'framer-motion'
import { t } from '@/i18n'

type FlowNodeId = 'employer' | 'employee' | 'perx' | 'provider'

interface FlowNode {
  id: FlowNodeId
  labelKey: string
  subKey: string
  x: number
  y: number
  width: number
  height: number
  /** When true, label + subtitle render inside the box (PerX hub). */
  stacked?: boolean
}

const FLOW_NODES: FlowNode[] = [
  {
    id: 'employer',
    labelKey: 'landing.flowEmployer',
    subKey: 'landing.flowEmployerSub',
    x: 200,
    y: 52,
    width: 112,
    height: 28,
  },
  {
    id: 'employee',
    labelKey: 'landing.flowEmployee',
    subKey: 'landing.flowEmployeeSub',
    x: 62,
    y: 200,
    width: 100,
    height: 28,
  },
  {
    id: 'perx',
    labelKey: 'landing.flowPerx',
    subKey: 'landing.flowPerxSub',
    x: 200,
    y: 200,
    width: 104,
    height: 44,
    stacked: true,
  },
  {
    id: 'provider',
    labelKey: 'landing.flowProvider',
    subKey: 'landing.flowProviderSub',
    x: 338,
    y: 200,
    width: 88,
    height: 28,
  },
]

const FLOW_PATHS = [
  { d: 'M 200 80 L 200 168' },
  { d: 'M 112 200 L 148 200' },
  { d: 'M 252 200 L 294 200' },
  { d: 'M 338 228 Q 200 300 62 228' },
] as const

function nodeRect(node: FlowNode) {
  return {
    x: node.x - node.width / 2,
    y: node.y - node.height / 2,
    width: node.width,
    height: node.height,
  }
}

export function EcosystemFlowVisual() {
  const reducedMotion = useReducedMotion()

  return (
    <div
      className="relative mx-auto w-full max-w-md lg:mx-0"
      aria-hidden
    >
      <div className="absolute inset-6 border border-[#1A1A1A]/10" />
      <div className="absolute inset-10 border border-[#1A1A1A]/6" />

      <svg viewBox="0 0 400 400" className="relative h-auto w-full text-ink">
        <defs>
          <radialGradient id="perx-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#8B4513" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#8B4513" stopOpacity="0" />
          </radialGradient>
        </defs>

        <circle cx="200" cy="200" r="90" fill="url(#perx-glow)" />

        {FLOW_PATHS.map(({ d }, i) => (
          <motion.path
            key={d}
            d={d}
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            strokeDasharray="6 5"
            opacity="0.25"
            initial={reducedMotion ? undefined : { pathLength: 0, opacity: 0 }}
            animate={
              reducedMotion ? { opacity: 0.25 } : { pathLength: 1, opacity: 0.25 }
            }
            transition={{
              duration: 1.2,
              delay: 0.3 + i * 0.15,
              ease: [0.25, 0.1, 0.25, 1],
            }}
          />
        ))}

        {!reducedMotion &&
          FLOW_PATHS.map(({ d }, i) => (
            <circle key={`dot-${d}`} r="3" fill="#8B4513">
              <animateMotion
                dur={`${3 + i * 0.5}s`}
                repeatCount="indefinite"
                path={d}
                begin={`${i * 0.8}s`}
              />
            </circle>
          ))}

        {FLOW_NODES.map((node, i) => {
          const { x, y, height, stacked, id, labelKey, subKey } = node
          const rect = nodeRect(node)
          const isPerx = id === 'perx'

          return (
            <g key={id}>
              <motion.rect
                x={rect.x}
                y={rect.y}
                width={rect.width}
                height={rect.height}
                fill={isPerx ? '#FAF9F5' : '#F4F1EA'}
                stroke={isPerx ? '#8B4513' : 'currentColor'}
                strokeWidth={isPerx ? 1.5 : 1}
                initial={reducedMotion ? undefined : { opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + i * 0.1, duration: 0.5 }}
                style={{ transformOrigin: `${x}px ${y}px` }}
              />
              <motion.text
                x={x}
                y={stacked ? y - 6 : y + 1}
                textAnchor="middle"
                className="fill-ink font-sans text-[10px] font-medium uppercase tracking-wide"
                initial={reducedMotion ? undefined : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 + i * 0.1 }}
              >
                {t(labelKey)}
              </motion.text>
              <motion.text
                x={x}
                y={stacked ? y + 10 : y + height / 2 + 12}
                textAnchor="middle"
                className="fill-[#1A1A1A]/55 font-sans text-[8px] uppercase tracking-wide"
                initial={reducedMotion ? undefined : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 + i * 0.1 }}
              >
                {t(subKey)}
              </motion.text>
            </g>
          )
        })}
      </svg>

      <motion.div
        className="absolute bottom-4 left-1/2 -translate-x-1/2 border border-[#1A1A1A]/12 bg-paper px-4 py-1.5"
        animate={reducedMotion ? undefined : { opacity: [0.7, 1, 0.7] }}
        transition={
          reducedMotion
            ? undefined
            : { duration: 3, repeat: Infinity, ease: 'easeInOut' }
        }
      >
        <p className="whitespace-nowrap font-mono text-[10px] uppercase tracking-widest text-sienna">
          {t('landing.closedLoop')}
        </p>
      </motion.div>
    </div>
  )
}
