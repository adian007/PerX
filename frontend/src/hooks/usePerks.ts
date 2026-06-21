import { useQuery } from '@tanstack/react-query'
import { fetchCategories, fetchPerks, fetchRecommendations, isAuthenticated } from '@/api/client'
import { mapApiPerk } from '@/lib/perks'

export function useRecommendations() {
  return useQuery({
    queryKey: ['recommendations'],
    queryFn: async () => {
      const data = await fetchRecommendations(3)
      return (data?.perks ?? []).map(mapApiPerk)
    },
    staleTime: 60_000,
    enabled: isAuthenticated(),
  })
}

export function useAllPerks() {
  return useQuery({
    queryKey: ['perks'],
    queryFn: async () => {
      const data = await fetchPerks({ limit: 50 })
      return (data?.perks ?? []).map(mapApiPerk)
    },
    staleTime: 60_000,
    enabled: isAuthenticated(),
  })
}

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => fetchCategories(),
    staleTime: 120_000,
    enabled: isAuthenticated(),
  })
}
