import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Package } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError, fetchPackages, selectPackage } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { t } from '@/i18n'
import { formatPerkPrice } from '@/lib/perks'
import { cn } from '@/lib/utils'

export function PackagesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [submittingId, setSubmittingId] = useState<string | null>(null)

  const { data: packages = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['packages'],
    queryFn: fetchPackages,
  })

  const handleSelect = async (packageId: string, packageName: string) => {
    setSubmittingId(packageId)
    try {
      await selectPackage(packageId)
      await queryClient.invalidateQueries({ queryKey: ['my-selections'] })
      toast.success(t('packages.submitted'), {
        description: `${packageName} ${t('packages.submittedDesc')}`,
      })
      navigate('/employee/selections')
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : t('packages.failed')
      toast.error(t('packages.failed'), { description: message })
    } finally {
      setSubmittingId(null)
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h1 className="font-display text-4xl font-semibold italic">{t('packages.title')}</h1>
        <p className="max-w-2xl text-muted">{t('packages.body')}</p>
      </div>

      {isLoading && <p className="text-muted">{t('common.loading')}</p>}
      {isError && (
        <button type="button" onClick={() => void refetch()} className="text-sm text-sienna underline">
          {t('common.retry')}
        </button>
      )}

      {!isLoading && !isError && packages.length === 0 && (
        <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
          <Package className="mx-auto h-8 w-8 text-muted" strokeWidth={1.5} />
          <p className="mt-4 font-display text-xl">{t('packages.title')}</p>
          <p className="mt-2 text-sm text-muted">{t('packages.body')}</p>
        </div>
      )}

      <div className="grid items-stretch gap-6 md:grid-cols-2 lg:grid-cols-3">
        {packages.map((pkg) => {
          const isDemo = pkg.name === 'Wellness Starter'
          const providers = [...new Set(pkg.items.map((i) => i.provider_name))]

          return (
            <Card
              key={pkg.id}
              className={cn(
                'flex h-full flex-col',
                isDemo && 'border-sienna ring-1 ring-sienna/30',
              )}
            >
              <CardHeader className="space-y-3 pb-4">
                <div className="flex min-h-[2rem] flex-wrap items-start gap-2">
                  <CardTitle className="font-display text-xl leading-tight">{pkg.name}</CardTitle>
                  {isDemo && <Badge variant="accent">{t('packages.demoBundle')}</Badge>}
                  {providers.length > 1 && (
                    <Badge variant="outline">
                      {providers.length} {t('packages.providers')}
                    </Badge>
                  )}
                </div>
                <p className="min-h-[2.75rem] text-sm leading-relaxed text-muted">
                  {pkg.description ?? t('packages.fallbackDesc')}
                </p>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col gap-4 pt-0">
                <p className="font-mono text-lg tabular-nums">
                  {formatPerkPrice(pkg.total_price_cents, pkg.currency_code)}
                </p>
                <ul className="min-h-[7.5rem] flex-1 space-y-3 border-t border-border pt-4 text-sm">
                  {pkg.items.map((item) => (
                    <li key={item.perk_id} className="flex flex-col gap-0.5">
                      <span className="font-medium">{item.name}</span>
                      <span className="text-muted">
                        {item.provider_name} · {item.category}
                      </span>
                    </li>
                  ))}
                </ul>
                <Button
                  className="mt-auto w-full shrink-0"
                  disabled={submittingId === pkg.id}
                  onClick={() => void handleSelect(pkg.id, pkg.name)}
                >
                  {submittingId === pkg.id ? t('packages.submitting') : t('packages.submit')}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
