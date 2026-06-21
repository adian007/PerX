import { motion, useReducedMotion } from 'framer-motion'
import {
  Check,
  Dumbbell,
  Lock,
  MapPin,
  Sparkles,
  UtensilsCrossed,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { JourneyNode } from '@/types'

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  travel: MapPin,
  food: UtensilsCrossed,
  fitness: Dumbbell,
  wellness: Sparkles,
}

const STATUS_LABEL: Record<JourneyNode['status'], string> = {
  locked: 'E mbyllur',
  available: 'Gati',
  current: 'Hapi aktual',
  completed: 'Përfunduar',
}

interface BenefitPathMapProps {
  nodes: JourneyNode[]
  pathD: string
  selectedCategory: string | null
  onSelect: (node: JourneyNode) => void
}

export function BenefitPathMap({
  nodes,
  pathD,
  selectedCategory,
  onSelect,
}: BenefitPathMapProps) {
  const reducedMotion = useReducedMotion()

  const currentIndex = nodes.findIndex((n) => n.status === 'current')
  const lastCompletedIndex = nodes.reduce(
    (max, node, index) => (node.status === 'completed' ? index : max),
    -1,
  )
  const progressIndex =
    currentIndex >= 0 ? currentIndex : lastCompletedIndex >= 0 ? lastCompletedIndex : 0
  const progressRatio =
    nodes.length > 1 ? progressIndex / (nodes.length - 1) : nodes.length === 1 ? 1 : 0

  const completedCount = nodes.filter((n) => n.status === 'completed').length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-ink/10 pb-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Progresi</p>
          <p className="mt-1 font-display text-2xl font-semibold tabular-nums">
            {completedCount}{' '}
            <span className="text-lg font-normal text-muted">nga {nodes.length} hapa</span>
          </p>
        </div>
        <div className="flex gap-4 font-mono text-[10px] uppercase tracking-wider text-muted">
          {(['completed', 'current', 'available', 'locked'] as const).map((status) => (
            <span key={status} className="inline-flex items-center gap-1.5">
              <span
                className={cn(
                  'inline-block h-2 w-2 border border-ink',
                  status === 'completed' && 'bg-ink',
                  status === 'current' && 'border-sienna bg-sienna/20',
                  status === 'locked' && 'border-dashed opacity-40',
                )}
              />
              {STATUS_LABEL[status]}
            </span>
          ))}
        </div>
      </div>

      <div className="relative aspect-[20/9] w-full min-w-[320px]">
        <svg
          viewBox="0 0 800 360"
          className="absolute inset-0 h-full w-full"
          aria-hidden
        >
          <path
            d={pathD}
            fill="none"
            stroke="#1A1A1A"
            strokeWidth="1"
            strokeOpacity="0.12"
            strokeLinecap="round"
          />
          <motion.path
            d={pathD}
            fill="none"
            stroke="#8B4513"
            strokeWidth="2"
            strokeLinecap="round"
            initial={false}
            animate={{ strokeDashoffset: 1 - progressRatio }}
            transition={reducedMotion ? { duration: 0 } : { duration: 0.7, ease: 'easeInOut' }}
            style={{
              pathLength: 1,
              strokeDasharray: 1,
              strokeDashoffset: 1 - progressRatio,
            }}
          />
        </svg>

        {nodes.map((node) => {
          const Icon = CATEGORY_ICONS[node.category] ?? Sparkles
          const isSelected = selectedCategory === node.category
          const left = `${(node.x / 800) * 100}%`
          const top = `${(node.y / 360) * 100}%`

          return (
            <button
              key={node.category}
              type="button"
              onClick={() => onSelect(node)}
              className={cn(
                'group absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 outline-none',
                'focus-visible:ring-2 focus-visible:ring-sienna focus-visible:ring-offset-2 focus-visible:ring-offset-paper',
              )}
              style={{ left, top }}
              aria-label={`${node.label}: ${STATUS_LABEL[node.status]}`}
              aria-current={node.status === 'current' ? 'step' : undefined}
            >
              {node.status === 'current' && (
                <span className="font-mono text-[10px] uppercase tracking-widest text-sienna">
                  You are here
                </span>
              )}

              <span
                className={cn(
                  'relative flex h-14 w-14 items-center justify-center border-2 bg-paper transition-colors',
                  node.status === 'completed' && 'border-ink bg-ink text-cream',
                  node.status === 'current' && 'border-sienna bg-paper text-sienna ring-2 ring-sienna/12',
                  node.status === 'available' && 'border-ink/70 text-ink group-hover:border-sienna group-hover:text-sienna',
                  node.status === 'locked' && 'border-dashed border-ink/30 text-ink/35',
                  isSelected && node.status !== 'current' && 'ring-2 ring-sienna/40 ring-offset-2 ring-offset-paper',
                )}
              >
                {node.status === 'completed' ? (
                  <Check className="h-5 w-5" strokeWidth={2.5} />
                ) : node.status === 'locked' ? (
                  <Lock className="h-4 w-4" strokeWidth={2} />
                ) : (
                  <Icon className="h-5 w-5" strokeWidth={1.75} />
                )}

                {node.status === 'current' && !reducedMotion && (
                  <span className="absolute inset-0 animate-ping border border-sienna/40" />
                )}
              </span>

              <span
                className={cn(
                  'font-display text-sm leading-none',
                  node.status === 'locked' ? 'text-muted' : 'text-ink',
                  isSelected && 'font-semibold text-sienna',
                )}
              >
                {node.label}
              </span>

              <span className="font-mono text-[10px] tabular-nums text-muted">
                {Math.round(node.affinityScore * 100)}% match
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
