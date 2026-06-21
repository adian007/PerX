import { Link } from 'react-router-dom'
import { Heart, MessageSquareText, ChevronRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { t } from '@/i18n'
import { useWishlist } from '@/hooks/useWishlist'
import { useUserState } from '@/stores/userState'

export function LibraryPreview() {
  const { reviews } = useUserState()
  const { data: wishlist = [] } = useWishlist()

  const wishlistCount = wishlist.length
  const reviewCount = reviews.length

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold">{t('library.title')}</h2>
          <p className="mt-1 text-sm text-muted">{t('library.subtitle')}</p>
        </div>
        <Link
          to="/employee/saved"
          className="font-sans text-sm underline underline-offset-4 hover:text-sienna"
        >
          {t('common.viewAll')}
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link to="/employee/saved" className="group block">
          <Card className="h-full transition-colors group-hover:border-sienna/40">
            <CardContent className="flex items-center gap-4 p-6">
              <span className="flex h-12 w-12 items-center justify-center border border-ink/15 bg-paper">
                <Heart className="h-5 w-5 text-sienna" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-display text-lg font-semibold">{t('saved.wishlist')}</p>
                <p className="text-sm text-muted">
                  {wishlistCount === 0
                    ? t('library.wishlistEmpty')
                    : `${wishlistCount} ${
                        wishlistCount === 1
                          ? t('library.savedBenefit')
                          : t('library.savedBenefits')
                      }`}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 shrink-0 text-muted group-hover:text-sienna" />
            </CardContent>
          </Card>
        </Link>

        <Link to="/employee/saved?tab=reviews" className="group block">
          <Card className="h-full transition-colors group-hover:border-sienna/40">
            <CardContent className="flex items-center gap-4 p-6">
              <span className="flex h-12 w-12 items-center justify-center border border-ink/15 bg-paper">
                <MessageSquareText className="h-5 w-5 text-sienna" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-display text-lg font-semibold">{t('saved.reviews')}</p>
                <p className="text-sm text-muted">
                  {reviewCount === 0
                    ? t('library.reviewEmpty')
                    : `${reviewCount} ${
                        reviewCount === 1
                          ? t('library.reviewSubmitted')
                          : t('library.reviewsSubmitted')
                      }`}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 shrink-0 text-muted group-hover:text-sienna" />
            </CardContent>
          </Card>
        </Link>
      </div>
    </section>
  )
}
