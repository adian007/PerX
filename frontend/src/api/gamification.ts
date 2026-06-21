import { apiRequest, isAuthenticated } from '@/api/client'
import type { PerkReview, UserGamificationState } from '@/types'

export interface GamificationSnapshot {
  level: number
  class_label: string
  xp: number
  xp_to_next_level: number
  streak_days: number
  points_balance: number
  last_active_date: string | null
  completed_path_nodes: string[]
  unlocked_achievements: string[]
  unlocked_at_by_slug: Record<string, string>
  quiz_progress: Record<string, number>
  reviews: Array<{
    perk_id: string
    rating: number
    feedback: string
    submitted_at: string
  }>
  marathoner_miles: number
}

export function mapSnapshotToUserState(
  snapshot: GamificationSnapshot,
  current: UserGamificationState,
): UserGamificationState {
  return {
    ...current,
    level: snapshot.level,
    classLabel: snapshot.class_label,
    xp: snapshot.xp,
    xpToNextLevel: snapshot.xp_to_next_level,
    streakDays: snapshot.streak_days,
    pointsBalance: snapshot.points_balance,
    lastActiveDate: snapshot.last_active_date ?? current.lastActiveDate,
    completedPathNodes: snapshot.completed_path_nodes,
    unlockedAchievements: snapshot.unlocked_achievements,
    quizProgress: snapshot.quiz_progress,
    marathonerMiles: snapshot.marathoner_miles,
    reviews: snapshot.reviews.map(
      (review): PerkReview => ({
        perkId: review.perk_id,
        rating: review.rating,
        feedback: review.feedback,
        submittedAt: review.submitted_at,
      }),
    ),
  }
}

export async function fetchGamification(): Promise<GamificationSnapshot> {
  return apiRequest<GamificationSnapshot>('/api/v1/me/gamification')
}

export async function patchGamification(body: {
  marathoner_miles?: number
  record_daily_visit?: boolean
}): Promise<GamificationSnapshot> {
  return apiRequest<GamificationSnapshot>('/api/v1/me/gamification', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function completeJourneyNode(category: string): Promise<GamificationSnapshot> {
  return apiRequest<GamificationSnapshot>(`/api/v1/me/journey/${category}/complete`, {
    method: 'POST',
  })
}

export async function saveQuizScore(
  category: string,
  score: number,
  total: number,
): Promise<GamificationSnapshot> {
  return apiRequest<GamificationSnapshot>(`/api/v1/me/quiz/${category}`, {
    method: 'PUT',
    body: JSON.stringify({ score, total }),
  })
}

export async function unlockAchievement(slug: string): Promise<GamificationSnapshot> {
  return apiRequest<GamificationSnapshot>(`/api/v1/me/achievements/${slug}/unlock`, {
    method: 'POST',
  })
}

export async function submitReview(
  perkId: string,
  rating: number,
  feedback = '',
): Promise<GamificationSnapshot> {
  return apiRequest<GamificationSnapshot>('/api/v1/me/reviews', {
    method: 'POST',
    body: JSON.stringify({ perk_id: perkId, rating, feedback }),
  })
}

export function canSyncGamification(): boolean {
  return isAuthenticated()
}
