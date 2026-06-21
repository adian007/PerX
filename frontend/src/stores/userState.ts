import { create } from 'zustand'
import {
  canSyncGamification,
  completeJourneyNode as apiCompleteJourneyNode,
  fetchGamification,
  mapSnapshotToUserState,
  patchGamification,
  saveQuizScore as apiSaveQuizScore,
  submitReview as apiSubmitReview,
  unlockAchievement as apiUnlockAchievement,
} from '@/api/gamification'
import {
  DEFAULT_USER_STATE,
  LEVEL_THRESHOLDS,
  POINTS,
  type PerkReview,
  type UserGamificationState,
} from '@/types'
import {
  loadUserStateFromDexie,
  resetUserStateInDexie,
  saveUserStateToDexie,
} from '@/db/dexie'

interface UserStateStore extends UserGamificationState {
  hydrated: boolean
  unlockedAtBySlug: Record<string, string>
  hydrate: () => Promise<void>
  syncFromServer: () => Promise<void>
  reset: () => Promise<void>
  setDisplayName: (name: string) => void
  setWishlistIds: (ids: string[]) => void
  addPoints: (amount: number) => void
  addXp: (amount: number) => void
  toggleWishlist: (perkId: string) => void
  isWishlisted: (perkId: string) => boolean
  completePathNode: (category: string) => Promise<void>
  unlockAchievement: (slug: string) => Promise<void>
  setQuizScore: (category: string, score: number, total?: number) => Promise<void>
  addReview: (perkId: string, rating: number, feedback?: string) => Promise<void>
  hasReviewed: (perkId: string) => boolean
  getReview: (perkId: string) => PerkReview | undefined
  setMarathonerMiles: (miles: number) => Promise<void>
  recordDailyVisit: () => Promise<void>
}

function migrateLegacyState(state: UserGamificationState): UserGamificationState {
  const legacy = state as UserGamificationState & { reviewsSubmitted?: string[] }
  if (legacy.reviewsSubmitted?.length && !state.reviews?.length) {
    const now = new Date().toISOString()
    return {
      ...state,
      reviews: legacy.reviewsSubmitted.map((perkId) => ({
        perkId,
        rating: 5,
        feedback: '',
        submittedAt: now,
      })),
    }
  }
  if (!state.reviews) {
    return { ...state, reviews: [] }
  }
  return state
}

function persist(state: UserGamificationState) {
  void saveUserStateToDexie(state)
}

function computeLevel(xp: number): { level: number; classLabel: string; xpToNextLevel: number } {
  let level = 1
  let classLabel: string = LEVEL_THRESHOLDS[0].label
  for (const threshold of LEVEL_THRESHOLDS) {
    if (xp >= threshold.xp) {
      level = threshold.level
      classLabel = threshold.label
    }
  }
  const next = LEVEL_THRESHOLDS.find((t) => t.level === level + 1)
  return {
    level,
    classLabel,
    xpToNextLevel: next?.xp ?? LEVEL_THRESHOLDS[LEVEL_THRESHOLDS.length - 1].xp,
  }
}

function applySnapshot(
  set: (partial: Partial<UserStateStore> | ((s: UserStateStore) => Partial<UserStateStore>)) => void,
  get: () => UserStateStore,
  snapshot: Awaited<ReturnType<typeof fetchGamification>>,
) {
  const current = get()
  const next = mapSnapshotToUserState(snapshot, current)
  set({
    ...next,
    unlockedAtBySlug: snapshot.unlocked_at_by_slug,
  })
  persist(next)
}

export const useUserState = create<UserStateStore>((set, get) => ({
  ...DEFAULT_USER_STATE,
  unlockedAtBySlug: {},
  hydrated: false,

  hydrate: async () => {
    const saved = await loadUserStateFromDexie()
    if (saved) {
      set({ ...migrateLegacyState(saved), hydrated: true })
    } else {
      set({ ...DEFAULT_USER_STATE, hydrated: true })
    }
  },

  syncFromServer: async () => {
    if (!canSyncGamification()) return
    try {
      const snapshot = await fetchGamification()
      applySnapshot(set, get, snapshot)
    } catch {
      // server sync is best-effort; Dexie cache remains
    }
  },

  reset: async () => {
    const fresh = await resetUserStateInDexie()
    set({ ...fresh, unlockedAtBySlug: {}, hydrated: true })
  },

  setDisplayName: (name) => {
    set((s) => {
      const next = { ...s, displayName: name }
      persist(next)
      return next
    })
  },

  setWishlistIds: (ids) => {
    set((s) => {
      const next = { ...s, wishlistIds: ids }
      persist(next)
      return next
    })
  },

  addPoints: (amount) => {
    set((s) => {
      const next = { ...s, pointsBalance: s.pointsBalance + amount }
      persist(next)
      return next
    })
  },

  addXp: (amount) => {
    set((s) => {
      const newXp = s.xp + amount
      const { level, classLabel, xpToNextLevel } = computeLevel(newXp)
      const next = { ...s, xp: newXp, level, classLabel, xpToNextLevel }
      persist(next)
      return next
    })
  },

  toggleWishlist: (perkId) => {
    const { wishlistIds } = get()
    const exists = wishlistIds.includes(perkId)
    const nextIds = exists
      ? wishlistIds.filter((id) => id !== perkId)
      : [...wishlistIds, perkId]

    set((s) => {
      const next = { ...s, wishlistIds: nextIds }
      persist(next)
      return next
    })
  },

  isWishlisted: (perkId) => get().wishlistIds.includes(perkId),

  completePathNode: async (category) => {
    const { completedPathNodes } = get()
    if (completedPathNodes.includes(category)) return

    if (canSyncGamification()) {
      try {
        const snapshot = await apiCompleteJourneyNode(category)
        applySnapshot(set, get, snapshot)
        return
      } catch {
        // fall through to local update
      }
    }

    const { addPoints, addXp } = get()
    addPoints(POINTS.PATH_NODE)
    addXp(20)
    set((s) => {
      const next = {
        ...s,
        completedPathNodes: [...s.completedPathNodes, category],
      }
      persist(next)
      return next
    })
  },

  unlockAchievement: async (slug) => {
    const { unlockedAchievements } = get()
    if (unlockedAchievements.includes(slug)) return

    if (canSyncGamification()) {
      try {
        const snapshot = await apiUnlockAchievement(slug)
        applySnapshot(set, get, snapshot)
        return
      } catch {
        // fall through to local update
      }
    }

    set((s) => {
      const next = {
        ...s,
        unlockedAchievements: [...s.unlockedAchievements, slug],
      }
      persist(next)
      return next
    })
  },

  setQuizScore: async (category, score, total) => {
    if (canSyncGamification() && total !== undefined) {
      try {
        const snapshot = await apiSaveQuizScore(category, score, total)
        applySnapshot(set, get, snapshot)
        return
      } catch {
        // fall through to local update
      }
    }

    set((s) => {
      const prev = s.quizProgress[category] ?? 0
      const next = {
        ...s,
        quizProgress: { ...s.quizProgress, [category]: Math.max(prev, score) },
      }
      persist(next)
      return next
    })
  },

  addReview: async (perkId, rating, feedback = '') => {
    if (canSyncGamification()) {
      try {
        const snapshot = await apiSubmitReview(perkId, rating, feedback)
        applySnapshot(set, get, snapshot)
        return
      } catch {
        // fall through to local update
      }
    }

    const { reviews, addPoints, addXp } = get()
    const existing = reviews.find((r) => r.perkId === perkId)
    const entry: PerkReview = {
      perkId,
      rating,
      feedback,
      submittedAt: existing?.submittedAt ?? new Date().toISOString(),
    }

    if (!existing) {
      addPoints(POINTS.REVIEW)
      addXp(10)
    }

    set((s) => {
      const nextReviews = existing
        ? s.reviews.map((r) => (r.perkId === perkId ? entry : r))
        : [...s.reviews, entry]
      const next = { ...s, reviews: nextReviews }
      persist(next)
      return next
    })
  },

  hasReviewed: (perkId) => get().reviews.some((r) => r.perkId === perkId),

  getReview: (perkId) => get().reviews.find((r) => r.perkId === perkId),

  setMarathonerMiles: async (miles) => {
    if (canSyncGamification()) {
      try {
        const snapshot = await patchGamification({ marathoner_miles: miles })
        applySnapshot(set, get, snapshot)
        return
      } catch {
        // fall through to local update
      }
    }

    set((s) => {
      const next = { ...s, marathonerMiles: miles }
      persist(next)
      if (miles >= 100) {
        void get().unlockAchievement('marathoner')
      }
      return next
    })
  },

  recordDailyVisit: async () => {
    const today = new Date().toISOString().slice(0, 10)
    const { lastActiveDate } = get()
    if (lastActiveDate === today) return

    if (canSyncGamification()) {
      try {
        const snapshot = await patchGamification({ record_daily_visit: true })
        applySnapshot(set, get, snapshot)
        return
      } catch {
        // fall through to local update
      }
    }

    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toISOString().slice(0, 10)
    const { streakDays } = get()
    const nextStreak = lastActiveDate === yesterdayStr ? streakDays + 1 : 1

    set((s) => {
      const next = {
        ...s,
        lastActiveDate: today,
        streakDays: nextStreak,
        pointsBalance: s.pointsBalance + POINTS.DAILY_STREAK,
      }
      persist(next)
      return next
    })
  },
}))
