import { Heart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { t } from '@/i18n'
import type { Perk } from '@/types'
import { cn } from '@/lib/utils'

interface PerkCardProps {
  perk: Perk
  wishlisted: boolean
  claiming?: boolean
  onClaim: (perk: Perk) => void
  onClaimWithQuiz: (perk: Perk) => void
  onToggleWishlist: (perk: Perk) => void
  showReviewLink?: boolean
  onReview?: (perk: Perk) => void
}

export function PerkCard({
  perk,
  wishlisted,
  claiming = false,
  onClaim,
  onClaimWithQuiz,
  onToggleWishlist,
  showReviewLink,
  onReview,
}: PerkCardProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="min-w-0 flex-1 text-lg line-clamp-2">{perk.name}</CardTitle>
          <button
            type="button"
            onClick={() => onToggleWishlist(perk)}
            className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
            aria-label={wishlisted ? t('perks.wishlistRemove') : t('perks.wishlistAdd')}
          >
            <Heart
              className={cn(
                'h-5 w-5 transition-colors',
                wishlisted ? 'fill-sienna text-sienna' : 'text-ink',
              )}
            />
          </button>
        </div>
        <p className="font-mono text-sm tabular-nums">{perk.employee_price_formatted}</p>
      </CardHeader>
      <CardContent className="flex-1">
        <p className="text-sm text-muted">{perk.short_description}</p>
        {perk.reason_text && (
          <p className="mt-2 border-l-2 border-sienna/40 pl-2 text-xs text-muted">
            {perk.reason_text}
          </p>
        )}
      </CardContent>
      <CardFooter className="flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap">
        <Button size="sm" onClick={() => onClaim(perk)} disabled={claiming}>
          {claiming ? t('perks.claiming') : t('perks.claim')}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onClaimWithQuiz(perk)}
          disabled={claiming}
        >
          {t('perks.quizClaim')}
        </Button>
        {showReviewLink && onReview && (
          <Button size="sm" variant="ghost" onClick={() => onReview(perk)}>
            {t('perks.review')}
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}
