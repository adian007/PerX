import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError, fetchDemoInfo } from '@/api/client'
import { getPostLoginPath } from '@/lib/authRoutes'
import { t } from '@/i18n'
import { useAuthStore } from '@/stores/authStore'

function modeFromParams(searchParams: URLSearchParams): 'login' | 'register' {
  return searchParams.get('mode') === 'register' ? 'register' : 'login'
}

export function AuthPanel() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const mode = modeFromParams(searchParams)
  const queryClient = useQueryClient()
  const { login, register, loading } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [employerCode, setEmployerCode] = useState('ACME-DEMO')
  const [demoEmployeeEmail] = useState('mira.warm@example.com')
  const [demoEmployerEmail] = useState('hr@example.com')
  const [demoProviderEmail] = useState('flowfit@example.com')
  const [demoPassword, setDemoPassword] = useState('Demo1234')

  function setAuthMode(next: 'login' | 'register') {
    if (next === 'register') {
      setSearchParams({ mode: 'register' }, { replace: true })
      return
    }
    setSearchParams({}, { replace: true })
  }

  useEffect(() => {
    void fetchDemoInfo()
      .then((info) => {
        setEmployerCode(info.employer_code)
        setDemoPassword(info.demo_password)
      })
      .catch(() => {
        // demo-info unavailable when ALLOW_DEMO_MODE is off
      })
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (mode === 'login') {
        const user = await login(email, password)
        toast.success(t('auth.welcomeBack'))
        await queryClient.invalidateQueries()
        navigate(getPostLoginPath(user))
      } else {
        await register(email, password, employerCode)
        toast.success(t('auth.accountCreated'), {
          description: (
            <span className="font-mono tabular-nums">{t('auth.welcomeBonus')}</span>
          ),
        })
        await queryClient.invalidateQueries()
        const user = useAuthStore.getState().user
        navigate(user ? getPostLoginPath(user) : '/employee/onboarding')
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Autentifikimi dështoi'
      toast.error(message)
    }
  }

  return (
    <div className="mx-auto w-full max-w-md border border-[#1A1A1A]/12 bg-paper p-8">
      <div className="mb-6 flex gap-2">
        <Button
          type="button"
          size="sm"
          variant={mode === 'login' ? 'default' : 'outline'}
          aria-pressed={mode === 'login'}
          onClick={() => setAuthMode('login')}
        >
          {t('auth.signIn')}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={mode === 'register' ? 'default' : 'outline'}
          aria-pressed={mode === 'register'}
          onClick={() => setAuthMode('register')}
        >
          {t('auth.register')}
        </Button>
      </div>

      {mode === 'register' && (
        <p className="mb-4 border-l-2 border-sienna pl-3 text-sm text-muted">{t('auth.joinBonus')}</p>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-xs uppercase tracking-wide text-muted">
            {t('auth.email')}
          </label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ti@kompania.com"
          />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block text-xs uppercase tracking-wide text-muted">
            {t('auth.password')}
          </label>
          <Input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min. 8 karaktere, shkronja dhe numra"
          />
        </div>
        {mode === 'register' && (
          <div>
            <label
              htmlFor="employerCode"
              className="mb-1 block text-xs uppercase tracking-wide text-muted"
            >
              {t('auth.employerCode')}
            </label>
            <Input
              id="employerCode"
              required
              value={employerCode}
              onChange={(e) => setEmployerCode(e.target.value.toUpperCase())}
              placeholder="ACME-DEMO"
            />
          </div>
        )}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? t('auth.pleaseWait') : mode === 'login' ? t('auth.signIn') : t('auth.createAccount')}
        </Button>
      </form>

      <p className="mt-6 text-xs text-muted">
        {t('auth.demoEmployee')}: <span className="font-mono">{demoEmployeeEmail}</span>
        <br />
        {t('auth.demoEmployer')}: <span className="font-mono">{demoEmployerEmail}</span>
        <br />
        {t('auth.demoProvider')}: <span className="font-mono">{demoProviderEmail}</span>
        <br />
        {t('auth.passwordLabel')}: <span className="font-mono">{demoPassword}</span>
        <br />
        {t('auth.employerCode')}: <span className="font-mono">{employerCode}</span>
      </p>
      <div className="mt-2 flex flex-col gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={() => {
            setEmail(demoEmployeeEmail)
            setPassword(demoPassword)
            setAuthMode('login')
          }}
        >
          {t('auth.fillEmployeeDemo')}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={() => {
            setEmail(demoEmployerEmail)
            setPassword(demoPassword)
            setAuthMode('login')
          }}
        >
          {t('auth.fillEmployerDemo')}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={() => {
            setEmail(demoProviderEmail)
            setPassword(demoPassword)
            setAuthMode('login')
          }}
        >
          {t('auth.fillProviderDemo')}
        </Button>
      </div>
    </div>
  )
}
