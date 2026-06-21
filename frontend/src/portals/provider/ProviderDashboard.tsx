import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchProviderAnalytics, fetchProviderPerks, fetchProviderProfile } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { t } from '@/i18n'
import { formatPerkPrice } from '@/lib/perks'
import { useAuthStore } from '@/stores/authStore'

export function ProviderDashboard() {
  const navigate = useNavigate()
  const { logout } = useAuthStore()

  const {
    data: profile,
    isLoading: profileLoading,
    isError: profileError,
    refetch: refetchProfile,
  } = useQuery({
    queryKey: ['provider-profile'],
    queryFn: fetchProviderProfile,
  })

  const {
    data: perksData,
    isLoading: perksLoading,
    isError: perksError,
    refetch: refetchPerks,
  } = useQuery({
    queryKey: ['provider-perks'],
    queryFn: fetchProviderPerks,
  })

  const {
    data: analytics,
    isLoading: analyticsLoading,
    isError: analyticsError,
    refetch: refetchAnalytics,
  } = useQuery({
    queryKey: ['provider-analytics'],
    queryFn: fetchProviderAnalytics,
  })

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const currency =
    (perksData?.perks[0]?.currency_code as string | undefined) ?? 'ALL'

  const formatPerkPriceFromApi = (perk: {
    employee_price_cents?: number
    employee_price_formatted?: string
    currency_code?: string
  }) => {
    if (typeof perk.employee_price_cents === 'number') {
      return formatPerkPrice(
        perk.employee_price_cents,
        (perk.currency_code as string | undefined) ?? currency,
      )
    }
    return String(perk.employee_price_formatted ?? '')
  }

  const queryError = profileError || perksError || analyticsError

  return (
    <div className="min-h-screen bg-cream">
      <header className="sticky top-0 z-50 border-b border-border bg-cream">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-sans text-xl font-semibold text-ink">{t('provider.title')}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/">{t('provider.marketplace')}</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              {t('common.signOut')}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-12 px-6 py-12">
        <div>
          <h1 className="font-display text-3xl font-semibold italic">
            {profileLoading ? t('common.loading') : (profile?.company_name ?? t('provider.dashboard'))}
          </h1>
          <p className="mt-2 text-muted">{t('provider.paymentsNote')}</p>
          {queryError && (
            <p className="mt-2 text-sm text-sienna">
              {t('common.loading')}{' '}
              <button
                type="button"
                className="underline"
                onClick={() => {
                  void refetchProfile()
                  void refetchPerks()
                  void refetchAnalytics()
                }}
              >
                {t('common.retry')}
              </button>
            </p>
          )}
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="font-sans text-sm text-muted">{t('provider.listedPerks')}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-mono text-3xl tabular-nums">
                {analyticsLoading ? '…' : (analytics?.total_perks ?? 0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="font-sans text-sm text-muted">{t('provider.redemptions')}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-mono text-3xl tabular-nums">
                {analyticsLoading ? '…' : (analytics?.total_redemptions ?? 0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="font-sans text-sm text-muted">{t('provider.simulatedRevenue')}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-mono text-3xl tabular-nums">
                {analyticsLoading
                  ? '…'
                  : formatPerkPrice(analytics?.total_revenue_cents ?? 0, currency)}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="font-sans text-lg">{t('provider.perkPerformance')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {analyticsLoading ? (
              <p className="text-sm text-muted">{t('common.loading')}</p>
            ) : analyticsError ? (
              <p className="text-sm text-sienna">
                {t('common.loading')}{' '}
                <button type="button" className="underline" onClick={() => void refetchAnalytics()}>
                  {t('common.retry')}
                </button>
              </p>
            ) : analytics && analytics.perk_stats.length > 0 ? (
              analytics.perk_stats.map((stat) => (
                <div
                  key={stat.perk_id}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2 last:border-0"
                >
                  <div>
                    <p className="font-medium">{stat.perk_name}</p>
                    <p className="text-sm capitalize text-muted">{stat.category}</p>
                  </div>
                  <div className="text-right font-mono text-sm tabular-nums">
                    <p>
                      {stat.selection_count} {t('common.selections')}
                    </p>
                    <p className="text-muted">
                      {formatPerkPrice(stat.revenue_cents, currency)}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
                <p className="text-sm text-muted">{t('provider.perkPerformance')}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-sans text-lg">{t('provider.listings')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {perksLoading ? (
              <p className="text-sm text-muted">{t('common.loading')}</p>
            ) : perksError ? (
              <p className="text-sm text-sienna">
                {t('common.loading')}{' '}
                <button type="button" className="underline" onClick={() => void refetchPerks()}>
                  {t('common.retry')}
                </button>
              </p>
            ) : perksData && perksData.perks.length > 0 ? (
              perksData.perks.map((perk) => (
                <div
                  key={String(perk.id)}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2 last:border-0"
                >
                  <div>
                    <p className="font-medium">{String(perk.name ?? t('provider.perkFallback'))}</p>
                    <p className="text-sm capitalize text-muted">{String(perk.category ?? '')}</p>
                  </div>
                  <p className="font-mono text-sm tabular-nums">{formatPerkPriceFromApi(perk)}</p>
                </div>
              ))
            ) : (
              <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
                <p className="text-sm text-muted">{t('provider.listings')}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
