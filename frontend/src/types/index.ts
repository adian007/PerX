export interface UserGamificationState {
  displayName: string
  level: number
  classLabel: string
  xp: number
  xpToNextLevel: number
  streakDays: number
  pointsBalance: number
  lastActiveDate: string
  wishlistIds: string[]
  completedPathNodes: string[]
  unlockedAchievements: string[]
  quizProgress: Record<string, number>
  reviews: PerkReview[]
  marathonerMiles: number
}

export interface PerkReview {
  perkId: string
  rating: number
  feedback: string
  submittedAt: string
}

export const LEVEL_THRESHOLDS = [
  { level: 1, label: 'I ri', xp: 0 },
  { level: 2, label: 'Eksplorues', xp: 150 },
  { level: 3, label: 'Ekspert përfitimesh', xp: 400 },
  { level: 4, label: 'Strateg', xp: 800 },
  { level: 5, label: 'Pro përfitimesh', xp: 1500 },
] as const

export const POINTS = {
  CLAIM_PERK: 75,
  QUIZ_BONUS: 50,
  PATH_NODE: 40,
  REVIEW: 25,
  QUIZ_PERFECT: 30,
  DAILY_STREAK: 10,
  WISHLIST: 15,
} as const

export const DEFAULT_USER_STATE: UserGamificationState = {
  displayName: '',
  level: 1,
  classLabel: 'I ri',
  xp: 0,
  xpToNextLevel: 150,
  streakDays: 0,
  pointsBalance: 0,
  lastActiveDate: new Date().toISOString().slice(0, 10),
  wishlistIds: [],
  completedPathNodes: [],
  unlockedAchievements: [],
  quizProgress: {},
  reviews: [],
  marathonerMiles: 0,
}

export interface Perk {
  id: string
  name: string
  category: string
  short_description: string
  employee_price_formatted: string
  employee_price_cents: number
  tags: string[]
  recommendation_score?: number
  reason_text?: string
}

export interface JourneyNode {
  category: string
  label: string
  status: 'locked' | 'available' | 'completed' | 'current'
  affinityScore: number
  perkCount: number
  reasonText: string
  x: number
  y: number
}

export interface Achievement {
  slug: string
  title: string
  description: string
  requirement: string
  unlocked: boolean
  unlockedAt?: string
  interactive?: boolean
  progress?: number
  goal?: number
}

export interface QuizQuestion {
  id: string
  question: string
  answer: boolean
  fact: string
}

export interface AiPrompt {
  id: string
  label: string
  response: string
}
