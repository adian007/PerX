import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { StarRating } from '@/components/editorial/StarRating'
import { t } from '@/i18n'
import { POINTS, type Perk } from '@/types'

interface ReviewDialogProps {
  perk: Perk | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (perkId: string, rating: number, feedback: string) => void
  alreadyReviewed?: boolean
}

export function ReviewDialog({
  perk,
  open,
  onOpenChange,
  onSubmit,
  alreadyReviewed = false,
}: ReviewDialogProps) {
  const [rating, setRating] = useState(0)
  const [feedback, setFeedback] = useState('')

  useEffect(() => {
    if (!open) {
      setRating(0)
      setFeedback('')
    }
  }, [open])

  const handleSubmit = () => {
    if (!perk || rating === 0) return
    onSubmit(perk.id, rating, feedback.trim())
    toast.success(t('review.submitted'), {
      description: (
        <span className="font-mono tabular-nums">+{POINTS.REVIEW} {t('common.points')}</span>
      ),
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t('review.title')} {perk?.name}
          </DialogTitle>
          <DialogDescription>
            {alreadyReviewed ? t('review.alreadyReviewed') : t('review.shareExperience')}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <StarRating value={rating} onChange={setRating} />
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder={t('review.placeholder')}
            rows={4}
            className="w-full rounded-none border border-[#1A1A1A]/12 bg-paper p-3 font-sans text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={rating === 0}>
            {t('review.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
