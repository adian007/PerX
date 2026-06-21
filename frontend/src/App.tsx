import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { RoleProtectedRoute } from '@/components/auth/RoleProtectedRoute'
import { EmployeeOnboardingGuard } from '@/components/auth/EmployeeOnboardingGuard'
import { EmployeeLayout } from '@/components/layout/EmployeeLayout'
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/LoginPage'
import { HomePage } from '@/portals/employee/HomePage'
import { JourneyPage } from '@/portals/employee/JourneyPage'
import { ExplorePage } from '@/portals/employee/ExplorePage'
import { AchievementsPage } from '@/portals/employee/AchievementsPage'
import { SavedPage } from '@/portals/employee/SavedPage'
import { QuizPage } from '@/portals/employee/QuizPage'
import { VisionPage } from '@/portals/employee/VisionPage'
import { PackagesPage } from '@/portals/employee/PackagesPage'
import { SelectionsPage } from '@/portals/employee/SelectionsPage'
import { OnboardingPage } from '@/portals/employee/OnboardingPage'
import { EmployerDashboard } from '@/portals/employer/EmployerDashboard'
import { ProviderDashboard } from '@/portals/provider/ProviderDashboard'
import { getAuthenticatedHomePath } from '@/lib/authRoutes'
import { isAuthenticated } from '@/api/client'

function PublicOrRedirect({ page }: { page: 'landing' | 'login' }) {
  if (isAuthenticated()) {
    return <Navigate to={getAuthenticatedHomePath()} replace />
  }
  return page === 'landing' ? <LandingPage /> : <LoginPage />
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PublicOrRedirect page="landing" />} />
        <Route path="/login" element={<PublicOrRedirect page="login" />} />
        <Route
          path="/employee"
          element={
            <RoleProtectedRoute allowedRoles={['employee']}>
              <EmployeeLayout />
            </RoleProtectedRoute>
          }
        >
          <Route element={<EmployeeOnboardingGuard />}>
            <Route index element={<HomePage />} />
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path="journey" element={<JourneyPage />} />
            <Route path="explore" element={<ExplorePage />} />
            <Route path="packages" element={<PackagesPage />} />
            <Route path="selections" element={<SelectionsPage />} />
            <Route path="saved" element={<SavedPage />} />
            <Route path="achievements" element={<AchievementsPage />} />
            <Route path="vision" element={<VisionPage />} />
            <Route path="quiz/:category?" element={<QuizPage />} />
          </Route>
        </Route>
        <Route
          path="/employer"
          element={
            <RoleProtectedRoute allowedRoles={['employer']}>
              <EmployerDashboard />
            </RoleProtectedRoute>
          }
        />
        <Route
          path="/provider"
          element={
            <RoleProtectedRoute allowedRoles={['provider']}>
              <ProviderDashboard />
            </RoleProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
