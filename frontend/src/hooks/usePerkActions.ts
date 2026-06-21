import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError, addToWishlist, logInteraction, quickAddPerk, removeFromWishlist } from '@/api/client'
import { useWishlist } from '@/hooks/useWishlist'
import { t } from '@/i18n'
import { useUserState } from '@/stores/userState'
import { type Perk } from '@/types'

export function usePerkActions() {
  const queryClient = useQueryClient()
  const { data: wishlist = [] } = useWishlist()
  const { syncFromServer, unlockAchievement } = useUserState()

  const isWishlisted = useCallback(
    (perkId: string) => wishlist.some((p) => p.id === perkId),
    [wishlist],
  )

  const claimPerk = useCallback(
    async (perk: Perk) => {
      try {
        const result = await quickAddPerk(perk.id)
        await logInteraction(perk.id, 'select').catch(() => undefined)
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['my-selections'] }),
          queryClient.invalidateQueries({ queryKey: ['employer-insights'] }),
          queryClient.invalidateQueries({ queryKey: ['budget'] }),
        ])
        await useUserState.getState().recordDailyVisit()
        await syncFromServer()
        toast.success(`${t('perks.submitted')} ${perk.name}`, {
          description: t('perks.submittedDesc'),
        })
        return result
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : t('perks.claimFailedDesc')
        toast.error(t('perks.claimFailed'), { description: message })
        throw err
      }
    },
    [queryClient, syncFromServer],
  )

  const toggleWishlistPerk = useCallback(
    async (perk: Perk) => {
      const previous = queryClient.getQueryData<Perk[]>(['wishlist']) ?? []
      const wasWishlisted = previous.some((p) => p.id === perk.id)

      queryClient.setQueryData<Perk[]>(['wishlist'], (old = []) =>
        wasWishlisted ? old.filter((p) => p.id !== perk.id) : [...old, perk],
      )

      try {
        if (wasWishlisted) {
          await removeFromWishlist(perk.id)
          await logInteraction(perk.id, 'remove_from_wishlist').catch(() => undefined)
        } else {
          await addToWishlist(perk.id)
          await logInteraction(perk.id, 'add_to_wishlist').catch(() => undefined)
          await syncFromServer()
          const newCount = (queryClient.getQueryData<Perk[]>(['wishlist']) ?? []).length
          if (newCount >= 5) {
            await unlockAchievement('wishlist-curator')
          }
        }
      } catch (err) {
        queryClient.setQueryData(['wishlist'], previous)
        const message = err instanceof ApiError ? err.message : t('perks.wishlistFailed')
        toast.error(message)
      }
    },
    [queryClient, syncFromServer, unlockAchievement],
  )

  return { claimPerk, toggleWishlistPerk, isWishlisted }
}
