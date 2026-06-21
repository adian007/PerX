import { t, tf } from '@/i18n'

const baseUrl = import.meta.env.VITE_API_URL ?? ''

function buildUrl(
  path: string,
  query?: Record<string, string | number | boolean | undefined>,
): string {
  const origin = baseUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173')
  const url = new URL(path, origin)
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined) url.searchParams.set(key, String(value))
    })
  }
  return url.toString()
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface AuthUser {
  id: string
  email: string
  role: string
  onboarding_completed: boolean
}

interface ApiEnvelope<T> {
  data: T
  meta?: { timestamp?: string; request_id?: string }
}

interface ApiErrorBody {
  error?: { code?: string; message?: string; details?: { errors?: unknown } }
  detail?: { code?: string; message?: string } | string
}

function parseError(status: number, body: ApiErrorBody): ApiError {
  const detail = body.error ?? (typeof body.detail === 'object' ? body.detail : null)
  const code = detail?.code ?? 'API_ERROR'
  let message =
    detail?.message ??
    (typeof body.detail === 'string' ? body.detail : tf('api.errors.requestFailed', String(status)))

  if (code === 'VALIDATION_ERROR' && body.error?.details?.errors) {
    const errors = body.error.details.errors as Array<{ msg?: string; loc?: string[] }>
    const first = errors[0]
    if (first?.msg) {
      message = first.loc?.includes('email') ? t('api.errors.invalidEmail') : first.msg
    }
  }

  return new ApiError(code, message, status)
}

export function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('perx_access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function isAuthenticated(): boolean {
  return Boolean(localStorage.getItem('perx_access_token'))
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  query?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const url = buildUrl(path, query)

  let res: Response
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...options.headers,
      },
    })
  } catch {
    const hint = baseUrl ? baseUrl : t('api.errors.viteDevHint')
    throw new ApiError('NETWORK_ERROR', tf('api.errors.networkError', hint), 0)
  }

  if (res.status === 204) {
    return undefined as T
  }

  const raw = await res.text()
  let body: ApiEnvelope<T> & ApiErrorBody & { error?: { code?: string; message?: string } }
  try {
    body = raw ? JSON.parse(raw) : ({} as typeof body)
  } catch {
    throw new ApiError(
      'API_ERROR',
      raw.trim().slice(0, 200) || tf('api.errors.requestFailed', String(res.status)),
      res.status,
    )
  }
  if (!res.ok) {
    if (body.error?.code) {
      throw new ApiError(
        body.error.code,
        body.error.message ?? t('api.errors.requestFailedGeneric'),
        res.status,
      )
    }
    throw parseError(res.status, body)
  }
  return body.data
}

// ── Auth ────────────────────────────────────────────────────────────────────

export async function fetchDemoInfo() {
  return apiRequest<{
    employer_code: string
    demo_email: string
    demo_password: string
  }>('/api/v1/auth/demo-info')
}

export async function login(email: string, password: string) {
  return apiRequest<{
    access_token: string
    refresh_token: string
    expires_in: number
    user: AuthUser
  }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function registerEmployee(email: string, password: string, employerCode: string) {
  return apiRequest<{ user_id: string; role: string; message: string }>(
    '/api/v1/auth/register',
    {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        role: 'employee',
        employer_code: employerCode,
      }),
    },
  )
}

export async function fetchMe() {
  return apiRequest<{
    id: string
    email: string
    first_name: string
    last_name: string
    onboarding_completed: boolean
    employer: { organization_name: string }
  }>('/api/v1/me')
}

export async function fetchBudget() {
  return apiRequest<{
    remaining_cents: number
    remaining_formatted: string
    allocated_formatted: string
    spent_formatted: string
    currency_code: string
  }>('/api/v1/me/budget')
}

// ── Perks & recommendations ─────────────────────────────────────────────────

export interface ApiPerk {
  id: string
  name: string
  category: string
  short_description: string
  employee_price_formatted: string
  employee_price_cents: number
  currency_code?: string
  tags: string[]
  recommendation_score?: number
  reason_text?: string
}

export async function fetchRecommendations(limit = 20) {
  return apiRequest<{
    perks: ApiPerk[]
    total: number
    explanation?: string | null
    explanation_pending?: boolean
  }>('/api/v1/recommendations', {}, { limit })
}

export async function fetchRecommendationExplanation() {
  return apiRequest<{ ready: boolean; explanation: string | null }>(
    '/api/v1/recommendations/explanation',
  )
}

export async function fetchCategories() {
  return apiRequest<{
    categories: Array<{
      category: string
      score: number
      perk_count: number
      color: string
    }>
  }>('/api/v1/recommendations/categories')
}

export async function fetchPerks(params?: { category?: string; limit?: number }) {
  return apiRequest<{ perks: ApiPerk[]; total: number }>(
    '/api/v1/perks',
    {},
    { limit: params?.limit ?? 50, category: params?.category },
  )
}

// ── Selections & wishlist ───────────────────────────────────────────────────

export async function quickAddPerk(perkId: string) {
  return apiRequest<{
    selection_id: string
    status: string
    message?: string
  }>('/api/v1/selections/quick-add', {
    method: 'POST',
    body: JSON.stringify({ perk_id: perkId }),
  })
}

export async function fetchWishlist() {
  return apiRequest<ApiPerk[]>('/api/v1/me/wishlist')
}

export async function addToWishlist(perkId: string) {
  return apiRequest<{ perk_id: string; added: boolean }>(
    `/api/v1/me/wishlist/${perkId}`,
    { method: 'POST' },
  )
}

export async function removeFromWishlist(perkId: string) {
  return apiRequest<void>(`/api/v1/me/wishlist/${perkId}`, { method: 'DELETE' })
}

export async function logInteraction(
  perkId: string,
  type: 'view' | 'click' | 'select' | 'add_to_wishlist' | 'remove_from_wishlist',
) {
  return apiRequest<{ logged: boolean }>('/api/v1/interactions', {
    method: 'POST',
    body: JSON.stringify({ perk_id: perkId, type }),
  })
}

// ── Chat (gemma2:2b) ────────────────────────────────────────────────────────

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatAction {
  type: 'link' | 'save_perk'
  label: string
  href?: string | null
  perk_id?: string | null
  perk_name?: string | null
}

export async function sendChatMessage(
  message: string,
  history: ChatHistoryMessage[] = [],
) {
  return apiRequest<{
    reply: string
    model: string
    source: string
    actions: ChatAction[]
  }>('/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  })
}

export async function fetchOnboardingExplanation() {
  return apiRequest<{ ready: boolean; explanation: string | null }>(
    '/api/v1/me/onboarding/explanation',
  )
}

export async function submitOnboarding(body: {
  lifestyle_tags: string[]
  preferred_categories: string[]
  budget_sensitivity: string
  wellness_priority: number
  family_situation: string
}) {
  return apiRequest<{
    onboarding_completed: boolean
    affinity_vector: Record<string, number>
    explanation_pending: boolean
    explanation: string | null
  }>('/api/v1/me/onboarding', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// ── Packages ────────────────────────────────────────────────────────────────

export interface PackagePerkItem {
  perk_id: string
  name: string
  category: string
  employee_price_cents: number
  provider_name: string
}

export interface ApiPackage {
  id: string
  name: string
  description: string | null
  category: string | null
  total_price_cents: number
  currency_code: string
  items: PackagePerkItem[]
}

export async function fetchPackages() {
  return apiRequest<ApiPackage[]>('/api/v1/packages')
}

export async function selectPackage(packageId: string) {
  return apiRequest<{
    package_id: string
    selection_ids: string[]
    status: string
    total_price_cents: number
    budget_remaining_cents: number
    message: string
  }>(`/api/v1/selections/package/${packageId}`, { method: 'POST' })
}

// ── Selections ──────────────────────────────────────────────────────────────

export interface SelectionListItem {
  id: string
  status: string
  price_cents_snapshot: number
  selected_at: string
  perk: {
    id: string
    name: string
    category: string
    employee_price_formatted?: string
    currency_code?: string
  }
}

export async function fetchMySelections(status?: string) {
  return apiRequest<SelectionListItem[]>(
    '/api/v1/me/selections',
    {},
    status ? { status } : undefined,
  )
}

export async function cancelSelection(selectionId: string) {
  return apiRequest<void>(`/api/v1/selections/${selectionId}`, { method: 'DELETE' })
}

// ── Employer ────────────────────────────────────────────────────────────────

export async function fetchEmployerOrganization() {
  return apiRequest<{
    id: string
    organization_name: string
    default_monthly_budget_cents: number
    default_currency_code: string
    invite_code: string
  }>('/api/v1/employer/organization')
}

export interface ApprovalQueueItem {
  selection_id: string
  package_id: string | null
  employee: { id: string; name: string; department: string | null }
  perk: { id: string; name: string; category: string; image_url: string | null }
  price_cents: number
  budget_remaining_after_cents: number
  selected_at: string
}

export async function fetchEmployerApprovals() {
  return apiRequest<ApprovalQueueItem[]>('/api/v1/employer/approvals')
}

export async function approveSelection(selectionId: string) {
  return apiRequest<{ status: string; notification_sent: boolean; approved_count: number }>(
    `/api/v1/employer/approvals/${selectionId}/approve`,
    { method: 'POST' },
  )
}

export async function rejectSelection(selectionId: string, reason: string) {
  return apiRequest<{ status: string; notification_sent: boolean; rejected_count: number }>(
    `/api/v1/employer/approvals/${selectionId}/reject`,
    { method: 'POST', body: JSON.stringify({ reason }) },
  )
}

export async function fetchEmployerInsights() {
  return apiRequest<{
    period: string
    currency_code: string
    employee_count: number
    total_allocated_cents: number
    total_spent_cents: number
    total_pending_cents: number
    total_remaining_cents: number
    utilization_pct: number
    pending_approval_count: number
    top_categories: Array<{ category: string; selection_count: number; spent_cents: number }>
    allocated_formatted: string
    spent_formatted: string
    pending_formatted: string
    remaining_formatted: string
    insight_summary: string
  }>('/api/v1/employer/insights')
}

// ── Provider ────────────────────────────────────────────────────────────────

export async function fetchProviderProfile() {
  return apiRequest<{
    id: string
    company_name: string
    description: string | null
    status: string
    avg_rating: number
    total_perks: number
  }>('/api/v1/provider/profile')
}

export async function fetchProviderPerks() {
  return apiRequest<{ perks: Array<Record<string, unknown>>; total: number }>(
    '/api/v1/provider/perks',
  )
}

export async function fetchProviderAnalytics() {
  return apiRequest<{
    total_perks: number
    total_redemptions: number
    avg_rating: number
    total_revenue_cents: number
    completed_payments_count: number
    perk_stats: Array<{
      perk_id: string
      perk_name: string
      category: string
      selection_count: number
      revenue_cents: number
    }>
    demand_by_category: Array<{ category: string; selection_count: number }>
  }>('/api/v1/provider/analytics')
}
