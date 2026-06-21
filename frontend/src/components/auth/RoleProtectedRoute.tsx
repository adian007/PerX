import { Navigate, useLocation } from 'react-router-dom'
import { isAuthenticated } from '@/api/client'
import { t } from '@/i18n'
import { useAuthStore } from '@/stores/authStore'

interface RoleProtectedRouteProps {
  children: React.ReactNode
  allowedRoles: string[]
}

export function RoleProtectedRoute({ children, allowedRoles }: RoleProtectedRouteProps) {
  const location = useLocation()
  const hydrated = useAuthStore((s) => s.hydrated)
  const user = useAuthStore((s) => s.user)

  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream font-sans text-muted">
        {t('common.loading')}
      </div>
    )
  }

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return children
}
