import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ApiError,
  approveSelection,
  fetchEmployerApprovals,
  rejectSelection,
  type ApprovalQueueItem,
} from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { t } from '@/i18n'
import { formatPerkPrice } from '@/lib/perks'

export function ApprovalQueue() {
  const queryClient = useQueryClient()
  const [rejectTarget, setRejectTarget] = useState<ApprovalQueueItem | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [actingId, setActingId] = useState<string | null>(null)

  const { data: approvals = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['employer-approvals'],
    queryFn: fetchEmployerApprovals,
    refetchInterval: 15000,
  })

  const handleApprove = async (selectionId: string) => {
    setActingId(selectionId)
    try {
      const result = await approveSelection(selectionId)
      await queryClient.invalidateQueries({ queryKey: ['employer-approvals'] })
      await queryClient.invalidateQueries({ queryKey: ['employer-insights'] })
      toast.success(t('employer.approvedToast'), {
        description: `${t('employer.approvedDesc')} ${result.approved_count} ${t('employer.approvedCount')}`,
      })
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t('employer.approveFailed')
      toast.error(t('employer.approveFailed'), { description: message })
    } finally {
      setActingId(null)
    }
  }

  const handleReject = async () => {
    if (!rejectTarget || !rejectReason.trim()) return
    setActingId(rejectTarget.selection_id)
    try {
      await rejectSelection(rejectTarget.selection_id, rejectReason.trim())
      await queryClient.invalidateQueries({ queryKey: ['employer-approvals'] })
      await queryClient.invalidateQueries({ queryKey: ['employer-insights'] })
      toast.success(t('employer.rejectedToast'))
      setRejectTarget(null)
      setRejectReason('')
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t('employer.rejectFailed')
      toast.error(t('employer.rejectFailed'), { description: message })
    } finally {
      setActingId(null)
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted">{t('employer.loadingQueue')}</p>
  }

  if (isError) {
    return (
      <p className="text-sm text-sienna">
        {t('employer.loadingQueue')}{' '}
        <button type="button" className="underline" onClick={() => void refetch()}>
          {t('common.retry')}
        </button>
      </p>
    )
  }

  if (approvals.length === 0) {
    return (
      <div className="border border-dashed border-ink/20 bg-paper p-10 text-center">
        <p className="font-display text-xl">{t('employer.approvalQueue')}</p>
        <p className="mt-2 text-sm text-muted">{t('employer.emptyQueue')}</p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-4">
        {approvals.map((item) => (
          <div
            key={item.selection_id}
            className="flex flex-col gap-3 border border-border p-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{item.perk.name}</span>
                {item.package_id && <Badge variant="accent">{t('employer.package')}</Badge>}
              </div>
              <p className="text-sm text-muted">
                {item.employee.name}
                {item.employee.department ? ` · ${item.employee.department}` : ''}
              </p>
              <p className="font-mono text-sm tabular-nums">
                {formatPerkPrice(item.price_cents)} · {item.perk.category}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                disabled={actingId === item.selection_id}
                onClick={() => void handleApprove(item.selection_id)}
              >
                {t('common.approve')}
              </Button>
              <Button
                variant="outline"
                disabled={actingId === item.selection_id}
                onClick={() => {
                  setRejectTarget(item)
                  setRejectReason('')
                }}
              >
                {t('common.reject')}
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Dialog open={Boolean(rejectTarget)} onOpenChange={(open) => !open && setRejectTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('employer.rejectTitle')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted">
              {rejectTarget?.perk.name} · {rejectTarget?.employee.name}
            </p>
            <Input
              placeholder={t('employer.rejectReason')}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRejectTarget(null)}>
                {t('common.cancel')}
              </Button>
              <Button disabled={!rejectReason.trim()} onClick={() => void handleReject()}>
                {t('employer.confirmReject')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Button variant="ghost" size="sm" className="mt-4" onClick={() => void refetch()}>
        {t('employer.refreshQueue')}
      </Button>
    </>
  )
}
