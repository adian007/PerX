import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BudgetRing } from '@/components/editorial/BudgetRing'
import { ApprovalQueue } from '@/components/employer/ApprovalQueue'
import { VisionJobStatus, VisionUpload } from '@/components/vision'
import { getVisionJob, type VisionJob, type VisionAnalyzeResponse } from '@/api/vision'
import { fetchEmployerInsights, fetchEmployerOrganization } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { t } from '@/i18n'
import { formatPerkPrice } from '@/lib/perks'
import { useAuthStore } from '@/stores/authStore'
import { useState } from 'react'

export function EmployerDashboard() {
  const navigate = useNavigate()
  const { logout } = useAuthStore()
  const [visionJob, setVisionJob] = useState<VisionJob | null>(null)

  const {
    data: org,
    isLoading: orgLoading,
    isError: orgError,
    refetch: refetchOrg,
  } = useQuery({
    queryKey: ['employer-org'],
    queryFn: fetchEmployerOrganization,
  })

  const {
    data: insights,
    isLoading: insightsLoading,
    isError: insightsError,
    refetch: refetchInsights,
  } = useQuery({
    queryKey: ['employer-insights'],
    queryFn: fetchEmployerInsights,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && data.pending_approval_count > 0 ? 15000 : false
    },
  })

  const currency = org?.default_currency_code ?? insights?.currency_code ?? 'ALL'
  const formatAmount = (cents: number) => formatPerkPrice(cents, currency)
  const insightsPending = insightsLoading || orgLoading

  async function handleSubmitted(payload: VisionAnalyzeResponse) {
    setVisionJob(payload.job)
    const latest = await getVisionJob(payload.job.id)
    setVisionJob(latest)
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-cream">
      <header className="sticky top-0 z-50 border-b border-border bg-cream">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-sans text-xl font-semibold text-ink">{t('employer.title')}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/login">{t('employer.switchAccount')}</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              {t('common.signOut')}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-12 px-6 py-12">
        <div>
          <h1 className="font-sans text-3xl font-semibold">{t('employer.budgetOverview')}</h1>
          <p className="mt-2 text-muted">
            {insights?.period ?? t('common.currentPeriod')} ·{' '}
            {org?.organization_name ?? t('common.yourOrg')}
          </p>
          {(insightsError || orgError) && (
            <p className="mt-2 text-sm text-sienna">
              {t('employer.loadingBudget')}{' '}
              <button
                type="button"
                className="underline"
                onClick={() => {
                  void refetchInsights()
                  void refetchOrg()
                }}
              >
                {t('common.retry')}
              </button>
            </p>
          )}
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="font-sans text-lg">{t('employer.utilization')}</CardTitle>
            </CardHeader>
            <CardContent className="flex justify-center py-6">
              {insightsPending ? (
                <p className="text-sm text-muted">{t('employer.loadingBudget')}</p>
              ) : insights ? (
                <BudgetRing
                  allocated={insights.total_allocated_cents}
                  spent={insights.total_spent_cents}
                  pending={insights.total_pending_cents}
                  formatAmount={formatAmount}
                />
              ) : (
                <p className="text-sm text-muted">{t('employer.loadingBudget')}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-sans text-lg flex items-center gap-2">
                {t('employer.engagement')}
                {insights && insights.pending_approval_count > 0 && (
                  <Badge variant="accent">
                    {insights.pending_approval_count} {t('common.pending')}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 font-mono text-sm tabular-nums">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="font-sans text-muted">{t('employer.activeEmployees')}</span>
                <span>{insightsPending ? '…' : (insights?.employee_count ?? '–')}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="font-sans text-muted">{t('employer.pendingApprovals')}</span>
                <span>{insightsPending ? '…' : (insights?.pending_approval_count ?? '–')}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="font-sans text-muted">{t('employer.utilizationPct')}</span>
                <span>
                  {insightsPending
                    ? '…'
                    : insights
                      ? `${insights.utilization_pct.toFixed(1)}%`
                      : '–'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="font-sans text-muted">{t('employer.unusedBudget')}</span>
                <span>
                  {insightsPending ? '…' : insights ? formatAmount(insights.total_remaining_cents) : '–'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="font-sans text-lg">{t('employer.insights')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {insightsPending ? (
              <p className="text-sm text-muted">{t('employer.loadingBudget')}</p>
            ) : insights ? (
              <>
                <p className="text-sm leading-relaxed text-muted">{insights.insight_summary}</p>
                {insights.top_categories.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs uppercase tracking-wide text-muted">
                      {t('employer.topCategories')}
                    </p>
                    {insights.top_categories.map((cat) => (
                      <div
                        key={cat.category}
                        className="flex items-center justify-between border-b border-border pb-2 text-sm"
                      >
                        <span className="capitalize">{cat.category}</span>
                        <span className="font-mono tabular-nums">
                          {cat.selection_count} {t('common.selections')} ·{' '}
                          {formatAmount(cat.spent_cents)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted">{t('employer.loadingBudget')}</p>
            )}
          </CardContent>
        </Card>

        <Card id="approval-queue">
          <CardHeader>
            <CardTitle className="font-sans text-lg">{t('employer.approvalQueue')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ApprovalQueue />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-sans text-lg">{t('employer.visionPlayground')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <VisionUpload onSubmitted={(payload) => void handleSubmitted(payload)} />
            <VisionJobStatus job={visionJob} />
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
