import { useQuery } from '@tanstack/react-query'
import { fetchWishlist, isAuthenticated } from '@/api/client'
import { mapApiPerk } from '@/lib/perks'
import type { Perk } from '@/types'

export function useWishlist() {
  return useQuery({
    queryKey: ['wishlist'],
    queryFn: async (): Promise<Perk[]> => {
      if (!isAuthenticated()) return []
      const data = await fetchWishlist()
      return (data ?? []).map(mapApiPerk)
    },
    staleTime: 30_000,
    enabled: isAuthenticated(),
  })
}
