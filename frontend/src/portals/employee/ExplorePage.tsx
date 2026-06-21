import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PerkCard } from '@/components/editorial/PerkCard'
import { PerkCardSkeleton } from '@/components/editorial/PerkCardSkeleton'
import { ReviewDialog } from '@/components/editorial/ReviewDialog'
import { useAllPerks } from '@/hooks/usePerks'
import { usePerkActions } from '@/hooks/usePerkActions'
import { CATEGORIES, type CategoryFilter } from '@/data/mockPerks'
import { categoryLabel, t } from '@/i18n'
import { useUserState } from '@/stores/userState'
import type { Perk } from '@/types'
import { cn } from '@/lib/utils'

export function ExplorePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialCategory = (searchParams.get('category') ?? 'all') as CategoryFilter
  const { data: perks = [], isLoading, isError, refetch } = useAllPerks()
  const { claimPerk, toggleWishlistPerk, isWishlisted } = usePerkActions()
  const { addReview, hasReviewed } = useUserState()

  const [category, setCategory] = useState<CategoryFilter>(
    CATEGORIES.includes(initialCategory) ? initialCategory : 'all',
  )
  const [search, setSearch] = useState('')
  const [reviewPerk, setReviewPerk] = useState<Perk | null>(null)
  const [claimingId, setClaimingId] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    return perks.filter((p) => {
      const matchCategory = category === 'all' || p.category === category
      const matchSearch =
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.short_description.toLowerCase().includes(q) ||
        p.tags.some((tag) => tag.toLowerCase().includes(q)) ||
        p.category.toLowerCase().includes(q)
      return matchCategory && matchSearch
    })
  }, [perks, category, search])

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
        <h1 className="font-display text-3xl font-semibold">{t('explore.title')}</h1>
        <p className="mt-2 text-muted">{t('explore.body')}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <Button
            key={cat}
            size="sm"
            variant={category === cat ? 'default' : 'outline'}
            onClick={() => setCategory(cat)}
            className={cn('capitalize')}
          >
            {categoryLabel(cat)}
          </Button>
        ))}
      </div>

      <Input
        placeholder={t('explore.searchPlaceholder')}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-md"
      />

      {isError && (
        <p className="text-sm text-sienna">
          {t('explore.loadError')}{' '}
          <button type="button" className="underline" onClick={() => void refetch()}>
            {t('common.retry')}
          </button>
        </p>
      )}

      {isLoading ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <PerkCardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((perk) => (
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
      ) : (
        <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
          <Search className="mx-auto h-8 w-8 text-muted" strokeWidth={1.5} />
          <p className="mt-4 font-display text-xl">{t('explore.empty')}</p>
          <p className="mt-2 text-sm text-muted">{t('explore.body')}</p>
          {(category !== 'all' || search.trim()) && (
            <Button
              className="mt-6"
              variant="accent"
              onClick={() => {
                setCategory('all')
                setSearch('')
              }}
            >
              {t('common.reset')}
            </Button>
          )}
        </div>
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
