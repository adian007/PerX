import { Outlet } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { EmployeeNav } from '@/components/layout/EmployeeNav'
import { BottomNav } from '@/components/layout/BottomNav'
import { OfflineBanner } from '@/components/layout/OfflineBanner'
import { AiConsultantDrawer } from '@/components/ai/AiConsultantDrawer'
import { t } from '@/i18n'

export function EmployeeLayout() {
  return (
    <div className="min-h-screen bg-cream pb-24 md:pb-8">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:border focus:border-ink focus:bg-cream focus:px-4 focus:py-2 focus:font-sans focus:text-sm focus:text-ink"
      >
        {t('a11y.skipToContent')}
      </a>
      <OfflineBanner />
      <Header />
      <EmployeeNav />
      <main id="main-content" className="mx-auto max-w-6xl px-6 py-12">
        <Outlet />
      </main>
      <BottomNav />
      <AiConsultantDrawer />
    </div>
  )
}
