import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { WireframeGlobe } from '@/components/editorial/WireframeGlobe'
import { LibraryPreview } from '@/components/editorial/LibraryPreview'
import { XpBar } from '@/components/editorial/XpBar'
import { PerkCard } from '@/components/editorial/PerkCard'
import { PerkCardSkeleton } from '@/components/editorial/PerkCardSkeleton'
import { useRecommendations } from '@/hooks/usePerks'
import { usePerkActions } from '@/hooks/usePerkActions'
import { useUserState } from '@/stores/userState'
import { t } from '@/i18n'
import { getGreeting } from '@/lib/utils'
import type { Perk } from '@/types'

export function HomePage() {
  const navigate = useNavigate()
  const reducedMotion = useReducedMotion()
  const { displayName } = useUserState()
  const { data: perks = [], isLoading, isError, refetch } = useRecommendations()
  const { claimPerk, toggleWishlistPerk, isWishlisted } = usePerkActions()
  const [claimingId, setClaimingId] = useState<string | null>(null)

  const handleClaim = async (perk: Perk) => {
    setClaimingId(perk.id)
    try {
      await claimPerk(perk)
    } finally {
      setClaimingId(null)
    }
  }

  const handleClaimWithQuiz = (perk: Perk) => {
    navigate(`/employee/quiz/${perk.category}?bonus=true&perkId=${perk.id}`)
  }

  return (
    <div className="space-y-12">
      <section className="relative overflow-hidden">
        <WireframeGlobe />
        <motion.div
          initial={reducedMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative max-w-xl space-y-3"
        >
          <h1 className="font-display text-4xl font-bold italic md:text-5xl">
            {getGreeting(displayName)}.
          </h1>
          <p className="font-sans text-lg text-muted">{t('home.networkAwaits')}</p>
        </motion.div>
      </section>

      <section className="space-y-4">
        <XpBar />
      </section>

      <Card className="border-sienna/30 bg-paper">
        <CardContent className="flex flex-col gap-4 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold">{t('home.packagesTitle')}</h2>
            <p className="mt-1 text-sm text-muted">{t('home.packagesBody')}</p>
          </div>
          <Button asChild>
            <Link to="/employee/packages">{t('home.browsePackages')}</Link>
          </Button>
        </CardContent>
      </Card>

      <LibraryPreview />

      <section className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="font-display text-2xl font-semibold">{t('home.recommended')}</h2>
          {isError && (
            <button
              type="button"
              onClick={() => void refetch()}
              className="text-sm underline text-sienna"
            >
              {t('common.retry')}
            </button>
          )}
        </div>
        {isLoading ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <PerkCardSkeleton key={i} />
            ))}
          </div>
        ) : perks.length === 0 ? (
          <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
            <Compass className="mx-auto h-8 w-8 text-muted" strokeWidth={1.5} />
            <p className="mt-4 font-display text-xl">{t('home.recommended')}</p>
            <p className="mt-2 text-sm text-muted">{t('explore.body')}</p>
            <Button asChild className="mt-6" variant="accent">
              <Link to="/employee/explore">{t('saved.browsePerks')}</Link>
            </Button>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {perks.map((perk) => (
              <PerkCard
                key={perk.id}
                perk={perk}
                wishlisted={isWishlisted(perk.id)}
                claiming={claimingId === perk.id}
                onClaim={(p) => void handleClaim(p)}
                onClaimWithQuiz={handleClaimWithQuiz}
                onToggleWishlist={(p) => void toggleWishlistPerk(p)}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <Link
          to="/employee/journey"
          className="inline-flex items-center gap-2 font-sans text-sm underline underline-offset-4 hover:text-sienna"
        >
          {t('home.continueJourney')}
        </Link>
      </section>
    </div>
  )
}
