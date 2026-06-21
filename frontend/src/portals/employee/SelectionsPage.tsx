import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ClipboardList } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError, cancelSelection, fetchMySelections } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { t } from '@/i18n'
import { normalizePriceDisplay } from '@/lib/perks'

const STATUS_TABS = [
  { value: '', labelKey: 'selections.all' },
  { value: 'pending_approval', labelKey: 'selections.pending' },
  { value: 'approved', labelKey: 'selections.approved' },
  { value: 'rejected', labelKey: 'selections.rejected' },
] as const

function statusLabel(status: string): string {
  switch (status) {
    case 'pending_approval':
      return t('selections.pendingApproval')
    case 'approved':
      return t('selections.approved')
    case 'rejected':
      return t('selections.rejected')
    case 'cancelled':
      return t('selections.cancelled')
    default:
      return status
  }
}

function statusVariant(status: string): 'default' | 'outline' | 'accent' {
  if (status === 'approved') return 'default'
  if (status === 'pending_approval') return 'accent'
  return 'outline'
}

export function SelectionsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const statusFilter = searchParams.get('status') ?? ''
  const queryClient = useQueryClient()

  const { data: selections = [], isLoading, isFetching } = useQuery({
    queryKey: ['my-selections', statusFilter],
    queryFn: () => fetchMySelections(statusFilter || undefined),
    refetchInterval: (query) => {
      const items = query.state.data ?? []
      return items.some((s) => s.status === 'pending_approval') ? 15000 : false
    },
  })

  const grouped = useMemo(() => {
    const byMinute = new Map<string, typeof selections>()
    for (const item of selections) {
      const key = item.selected_at.slice(0, 16)
      const group = byMinute.get(key) ?? []
      group.push(item)
      byMinute.set(key, group)
    }
    return [...byMinute.values()]
  }, [selections])

  const handleCancel = async (selectionId: string) => {
    try {
      await cancelSelection(selectionId)
      await queryClient.invalidateQueries({ queryKey: ['my-selections'] })
      toast.success(t('selections.cancelledToast'))
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : t('selections.cancelFailed')
      toast.error(t('selections.cancelFailed'), { description: message })
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h1 className="font-display text-4xl font-semibold italic">{t('selections.title')}</h1>
        <p className="text-muted">{t('selections.body')}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUS_TABS.map(({ value, labelKey }) => (
          <Button
            key={value || 'all'}
            size="sm"
            variant={statusFilter === value ? 'default' : 'outline'}
            onClick={() => setSearchParams(value ? { status: value } : {})}
          >
            {t(labelKey)}
          </Button>
        ))}
      </div>

      {isLoading && <p className="text-muted">{t('common.loading')}</p>}
      {!isLoading && selections.length === 0 && (
        <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
          <ClipboardList className="mx-auto h-8 w-8 text-muted" strokeWidth={1.5} />
          <p className="mt-4 font-display text-xl">{t('selections.title')}</p>
          <p className="mt-2 text-sm text-muted">{t('selections.empty')}</p>
          <Button asChild className="mt-6" variant="accent">
            <Link to="/employee/packages">{t('home.browsePackages')}</Link>
          </Button>
        </div>
      )}

      <div className="space-y-4">
        {grouped.map((group) => {
          const isPackageGroup = group.length > 1
          return (
            <Card key={group[0].id}>
              {isPackageGroup && (
                <CardHeader className="pb-2">
                  <CardTitle className="font-sans text-sm font-medium text-muted">
                    {t('selections.packageGroup')} · {group.length} {t('selections.perks')}
                  </CardTitle>
                </CardHeader>
              )}
              <CardContent className="space-y-4">
                {group.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-col gap-3 border-b border-border pb-4 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{item.perk.name}</span>
                        <Badge variant={statusVariant(item.status)}>
                          {statusLabel(item.status)}
                        </Badge>
                      </div>
                      <p className="text-sm capitalize text-muted">{item.perk.category}</p>
                      <p className="font-mono text-sm tabular-nums">
                        {normalizePriceDisplay(
                          item.perk.employee_price_formatted,
                          item.price_cents_snapshot,
                          item.perk.currency_code,
                        )}
                      </p>
                      {item.status === 'approved' && (
                        <p className="text-sm text-sienna">{t('selections.paymentNote')}</p>
                      )}
                    </div>
                    {item.status === 'pending_approval' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void handleCancel(item.id)}
                      >
                        {t('common.cancel')}
                      </Button>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {isFetching && !isLoading && (
        <p className="text-xs text-muted">{t('selections.refreshing')}</p>
      )}
    </div>
  )
}
