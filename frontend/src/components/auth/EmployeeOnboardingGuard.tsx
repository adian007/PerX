import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function EmployeeOnboardingGuard() {
  const location = useLocation()
  const user = useAuthStore((s) => s.user)

  if (
    user?.role === 'employee' &&
    !user.onboarding_completed &&
    !location.pathname.endsWith('/onboarding')
  ) {
    return <Navigate to="/employee/onboarding" replace />
  }

  if (user?.role === 'employee' && user.onboarding_completed && location.pathname.endsWith('/onboarding')) {
    return <Navigate to="/employee" replace />
  }

  return <Outlet />
}
