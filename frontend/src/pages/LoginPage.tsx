import { PublicNav } from '@/components/layout/PublicNav'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { t } from '@/i18n'

export function LoginPage() {
  return (
    <div className="min-h-screen bg-cream">
      <PublicNav />
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-12 px-6 py-16 lg:grid lg:grid-cols-2 lg:items-center lg:py-24">
        <div className="space-y-6">
          <h1 className="font-display text-4xl font-semibold italic md:text-5xl lg:text-6xl">
            {t('login.title')}
          </h1>
          <p className="text-lg leading-relaxed text-muted md:text-xl">{t('login.body')}</p>
          <ul className="space-y-3 text-base text-muted md:text-lg">
            <li className="flex items-center gap-2">
              <span className="font-mono text-sienna">{t('login.welcomePts')}</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="font-mono text-sienna">{t('login.claimPts')}</span>
            </li>
            <li className="flex items-center gap-2">{t('login.askPerx')}</li>
          </ul>
        </div>
        <AuthPanel />
      </main>
    </div>
  )
}
