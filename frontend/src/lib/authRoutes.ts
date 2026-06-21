import type { AuthUser } from '@/api/client'

const USER_KEY = 'perx_user'

export function persistAuthUser(user: AuthUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function readStoredAuthUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function clearStoredAuthUser(): void {
  localStorage.removeItem(USER_KEY)
}

export function getPostLoginPath(user: AuthUser): string {
  if (user.role === 'employer') return '/employer'
  if (user.role === 'provider') return '/provider'
  if (user.role === 'employee' && !user.onboarding_completed) return '/employee/onboarding'
  return '/employee'
}

export function getAuthenticatedHomePath(): string {
  const user = readStoredAuthUser()
  if (!user) return '/employee'
  return getPostLoginPath(user)
}
