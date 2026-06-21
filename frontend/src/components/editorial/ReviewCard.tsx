import { StarRating } from '@/components/editorial/StarRating'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Perk, PerkReview } from '@/types'

interface ReviewCardProps {
  review: PerkReview
  perk?: Perk
}

export function ReviewCard({ review, perk }: ReviewCardProps) {
  const submitted = new Date(review.submittedAt).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-lg">{perk?.name ?? 'Benefit'}</CardTitle>
            {perk && (
              <p className="font-mono text-sm tabular-nums text-muted">
                {perk.employee_price_formatted}
              </p>
            )}
          </div>
          {perk && (
            <Badge variant="outline" className="capitalize">
              {perk.category}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <StarRating value={review.rating} readonly />
        {review.feedback ? (
          <p className="border-l-2 border-sienna/40 pl-3 text-sm leading-relaxed text-muted">
            {review.feedback}
          </p>
        ) : (
          <p className="text-sm italic text-muted">No written feedback.</p>
        )}
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
          Reviewed {submitted}
        </p>
      </CardContent>
    </Card>
  )
}
