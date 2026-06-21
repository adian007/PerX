import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-none border px-2.5 py-0.5 font-mono text-xs font-medium tabular-nums transition-colors shadow-none',
  {
    variants: {
      variant: {
        default: 'border-ink bg-ink text-cream',
        outline: 'border-border bg-transparent text-ink',
        accent: 'border-sienna bg-sienna/10 text-sienna',
      },
    },
    defaultVariants: {
      variant: 'outline',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
