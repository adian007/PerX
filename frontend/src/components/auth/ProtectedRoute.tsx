import { Navigate, useLocation } from 'react-router-dom'
import { isAuthenticated } from '@/api/client'
import { t } from '@/i18n'
import { useAuthStore } from '@/stores/authStore'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const hydrated = useAuthStore((s) => s.hydrated)

  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream font-sans text-muted">
        {t('common.loading')}
      </div>
    )
  }

  if (!isAuthenticated()) {
    return <Navigate to="/" state={{ from: location.pathname }} replace />
  }

  return children
}
