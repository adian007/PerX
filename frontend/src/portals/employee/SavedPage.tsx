import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Heart, MessageSquareText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PerkCard } from '@/components/editorial/PerkCard'
import { ReviewCard } from '@/components/editorial/ReviewCard'
import { ReviewDialog } from '@/components/editorial/ReviewDialog'
import { useAllPerks } from '@/hooks/usePerks'
import { usePerkActions } from '@/hooks/usePerkActions'
import { useWishlist } from '@/hooks/useWishlist'
import { t } from '@/i18n'
import { useUserState } from '@/stores/userState'
import type { Perk } from '@/types'
import { cn } from '@/lib/utils'

type SavedTab = 'wishlist' | 'reviews'

export function SavedPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const urlTab = searchParams.get('tab') === 'reviews' ? 'reviews' : 'wishlist'
  const [tab, setTab] = useState<SavedTab>(urlTab)
  const [reviewPerk, setReviewPerk] = useState<Perk | null>(null)
  const [claimingId, setClaimingId] = useState<string | null>(null)

  useEffect(() => {
    setTab(urlTab)
  }, [urlTab])

  const {
    data: wishlist = [],
    isLoading: wishlistLoading,
    isError: wishlistError,
    refetch: refetchWishlist,
  } = useWishlist()
  const { data: allPerks = [] } = useAllPerks()
  const { claimPerk, toggleWishlistPerk, isWishlisted } = usePerkActions()
  const { reviews, addReview, hasReviewed } = useUserState()

  const perkById = useMemo(() => {
    const map = new Map<string, Perk>()
    for (const perk of allPerks) map.set(perk.id, perk)
    for (const perk of wishlist) map.set(perk.id, perk)
    return map
  }, [allPerks, wishlist])

  const sortedReviews = useMemo(
    () =>
      [...reviews].sort(
        (a, b) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime(),
      ),
    [reviews],
  )

  const switchTab = (next: SavedTab) => {
    setTab(next)
    setSearchParams(next === 'wishlist' ? {} : { tab: next })
  }

  const handleClaim = async (perk: Perk) => {
    setClaimingId(perk.id)
    try {
      await claimPerk(perk)
      if (!hasReviewed(perk.id)) {
        setReviewPerk(perk)
      }
    } finally {
      setClaimingId(null)
    }
  }

  const handleClaimWithQuiz = (perk: Perk) => {
    navigate(`/employee/quiz/${perk.category}?bonus=true&perkId=${perk.id}`)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold">{t('saved.title')}</h1>
        <p className="mt-2 max-w-2xl text-muted">{t('saved.body')}</p>
      </div>

      <div className="flex gap-2 border-b border-ink/10 pb-1">
        <button
          type="button"
          onClick={() => switchTab('wishlist')}
          className={cn(
            'inline-flex items-center gap-2 border-b-2 px-4 py-2 font-sans text-sm transition-colors',
            tab === 'wishlist'
              ? 'border-sienna text-sienna'
              : 'border-transparent text-muted hover:text-ink',
          )}
        >
          <Heart className="h-4 w-4" />
          {t('saved.wishlist')}
          <span className="font-mono text-xs tabular-nums">({wishlist.length})</span>
        </button>
        <button
          type="button"
          onClick={() => switchTab('reviews')}
          className={cn(
            'inline-flex items-center gap-2 border-b-2 px-4 py-2 font-sans text-sm transition-colors',
            tab === 'reviews'
              ? 'border-sienna text-sienna'
              : 'border-transparent text-muted hover:text-ink',
          )}
        >
          <MessageSquareText className="h-4 w-4" />
          {t('saved.reviews')}
          <span className="font-mono text-xs tabular-nums">({reviews.length})</span>
        </button>
      </div>

      {tab === 'wishlist' && (
        <section className="space-y-6">
          {wishlistLoading ? (
            <p className="text-muted">{t('saved.loadingWishlist')}</p>
          ) : wishlistError ? (
            <p className="text-sm text-sienna">
              {t('saved.wishlistError')}{' '}
              <button type="button" className="underline" onClick={() => void refetchWishlist()}>
                {t('common.retry')}
              </button>
            </p>
          ) : wishlist.length === 0 ? (
            <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
              <Heart className="mx-auto h-8 w-8 text-muted" strokeWidth={1.5} />
              <p className="mt-4 font-display text-xl">{t('saved.emptyWishlistTitle')}</p>
              <p className="mt-2 text-sm text-muted">{t('saved.emptyWishlistBody')}</p>
              <Button asChild className="mt-6" variant="accent">
                <Link to="/employee/explore">{t('saved.browsePerks')}</Link>
              </Button>
            </div>
          ) : (
            <>
              <p className="text-sm text-muted">
                {wishlist.length} {t('saved.savedCount')}
              </p>
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {wishlist.map((perk) => (
                  <PerkCard
                    key={perk.id}
                    perk={perk}
                    wishlisted={isWishlisted(perk.id)}
                    claiming={claimingId === perk.id}
                    onClaim={(p) => void handleClaim(p)}
                    onClaimWithQuiz={handleClaimWithQuiz}
                    onToggleWishlist={(p) => void toggleWishlistPerk(p)}
                    showReviewLink
                    onReview={setReviewPerk}
                  />
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {tab === 'reviews' && (
        <section className="space-y-6">
          {sortedReviews.length === 0 ? (
            <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
              <MessageSquareText className="mx-auto h-8 w-8 text-muted" strokeWidth={1.5} />
              <p className="mt-4 font-display text-xl">{t('saved.emptyReviewsTitle')}</p>
              <p className="mt-2 text-sm text-muted">{t('saved.emptyReviewsBody')}</p>
              <Button asChild className="mt-6" variant="accent">
                <Link to="/employee/explore">{t('saved.exploreBenefits')}</Link>
              </Button>
            </div>
          ) : (
            <>
              <p className="text-sm text-muted">
                {sortedReviews.length} {t('saved.reviewsSubmitted')}
              </p>
              <div className="grid gap-6 sm:grid-cols-2">
                {sortedReviews.map((review) => (
                  <ReviewCard
                    key={review.perkId}
                    review={review}
                    perk={perkById.get(review.perkId)}
                  />
                ))}
              </div>
            </>
          )}
        </section>
      )}

      <ReviewDialog
        perk={reviewPerk}
        open={!!reviewPerk}
        onOpenChange={(open) => !open && setReviewPerk(null)}
        onSubmit={addReview}
        alreadyReviewed={reviewPerk ? hasReviewed(reviewPerk.id) : false}
      />
    </div>
  )
}
