import { create } from 'zustand'
import {
  fetchMe,
  fetchWishlist,
  isAuthenticated,
  login as apiLogin,
  registerEmployee,
  type AuthUser,
} from '@/api/client'
import { clearStoredAuthUser, persistAuthUser, readStoredAuthUser } from '@/lib/authRoutes'
import { useUserState } from '@/stores/userState'

const TOKEN_KEY = 'perx_access_token'
const REFRESH_KEY = 'perx_refresh_token'
const USER_ID_KEY = 'perx_user_id'

interface AuthStore {
  user: AuthUser | null
  loading: boolean
  hydrated: boolean
  hydrate: () => Promise<void>
  login: (email: string, password: string) => Promise<AuthUser>
  register: (email: string, password: string, employerCode: string) => Promise<void>
  logout: () => void
  syncProfile: () => Promise<void>
  syncWishlist: () => Promise<void>
  syncGamification: () => Promise<void>
  setOnboardingCompleted: (completed: boolean) => void
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  loading: false,
  hydrated: false,

  hydrate: async () => {
    if (!isAuthenticated()) {
      set({ hydrated: true, user: null })
      return
    }

    const stored = readStoredAuthUser()
    if (stored && stored.role !== 'employee') {
      set({ hydrated: true, user: stored })
      useUserState.getState().recordDailyVisit()
      return
    }

    try {
      const me = await fetchMe()
      const user: AuthUser = {
        id: me.id,
        email: me.email,
        role: 'employee',
        onboarding_completed: me.onboarding_completed,
      }
      persistAuthUser(user)
      set({ hydrated: true, user })
      useUserState.getState().setDisplayName(me.first_name)
      await get().syncWishlist()
      await get().syncGamification()
      await useUserState.getState().recordDailyVisit()
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
      localStorage.removeItem(USER_ID_KEY)
      clearStoredAuthUser()
      set({ hydrated: true, user: null })
    }
  },

  login: async (email, password) => {
    set({ loading: true })
    try {
      const data = await apiLogin(email, password)
      const prevUserId = localStorage.getItem(USER_ID_KEY)
      if (prevUserId && prevUserId !== data.user.id) {
        await useUserState.getState().reset()
      }
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(REFRESH_KEY, data.refresh_token)
      localStorage.setItem(USER_ID_KEY, data.user.id)
      persistAuthUser(data.user)
      set({ user: data.user, loading: false })

      if (data.user.role === 'employee') {
        await get().syncProfile()
        await get().syncWishlist()
        await get().syncGamification()
      }

      await useUserState.getState().recordDailyVisit()
      return data.user
    } catch (err) {
      set({ loading: false })
      throw err
    }
  },

  register: async (email, password, employerCode) => {
    set({ loading: true })
    try {
      await registerEmployee(email, password, employerCode)
      await get().login(email, password)
      useUserState.getState().addPoints(50)
      useUserState.getState().addXp(50)
      set({ loading: false })
    } catch (err) {
      set({ loading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_ID_KEY)
    clearStoredAuthUser()
    void useUserState.getState().reset()
    set({ user: null })
  },

  syncProfile: async () => {
    const me = await fetchMe()
    const user: AuthUser = {
      id: me.id,
      email: me.email,
      role: 'employee',
      onboarding_completed: me.onboarding_completed,
    }
    persistAuthUser(user)
    set({ user })
    useUserState.getState().setDisplayName(me.first_name)
  },

  syncWishlist: async () => {
    try {
      const perks = await fetchWishlist()
      useUserState.getState().setWishlistIds(perks.map((p) => String(p.id)))
    } catch {
      // wishlist sync is best-effort
    }
  },

  syncGamification: async () => {
    await useUserState.getState().syncFromServer()
  },

  setOnboardingCompleted: (completed) => {
    const current = get().user
    if (!current) return
    const user = { ...current, onboarding_completed: completed }
    persistAuthUser(user)
    set({ user })
  },
}))
