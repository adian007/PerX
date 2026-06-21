import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '@/App'
import { Toaster } from '@/components/ui/sonner'
import { useAuthStore } from '@/stores/authStore'
import { useUserState } from '@/stores/userState'
import '@/index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function Bootstrap() {
  const hydrateUser = useUserState((s) => s.hydrate)
  const hydrateAuth = useAuthStore((s) => s.hydrate)

  useEffect(() => {
    void hydrateUser()
    void hydrateAuth()
  }, [hydrateUser, hydrateAuth])

  return (
    <>
      <App />
      <Toaster />
    </>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Bootstrap />
    </QueryClientProvider>
  </StrictMode>,
)
