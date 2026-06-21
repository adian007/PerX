import type { ApiPerk } from '@/api/client'
import { t } from '@/i18n'
import type { Perk } from '@/types'

/** Mirror backend format_money for ALL / sq-AL. */
export function formatPerkPrice(
  cents: number,
  currencyCode = 'ALL',
  locale = 'sq-AL',
): string {
  if (cents <= 0) return t('common.included')
  const amount = cents / 100

  if (currencyCode === 'ALL' && locale.startsWith('sq')) {
    if (amount === Math.floor(amount)) {
      const grouped = Math.floor(amount).toLocaleString('de-DE')
      return `${grouped} Lek`
    }
    const whole = amount.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    return `${whole} Lek`
  }

  const symbols: Record<string, string> = { EUR: '€', USD: '$', GBP: '£' }
  if (symbols[currencyCode]) {
    return `${symbols[currencyCode]}${amount.toLocaleString('en', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
  }

  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${currencyCode}`
  }
}

/** Re-format API prices in Lek — never trust legacy EUR strings from the backend. */
export function mapApiPerk(
  p: ApiPerk & { description?: string; currency_code?: string },
): Perk {
  const currency = p.currency_code ?? 'ALL'
  return {
    id: String(p.id),
    name: p.name,
    category: p.category,
    short_description: p.short_description ?? p.description ?? '',
    employee_price_formatted: formatPerkPrice(p.employee_price_cents, currency),
    employee_price_cents: p.employee_price_cents,
    tags: p.tags ?? [],
    recommendation_score: p.recommendation_score,
    reason_text: p.reason_text,
  }
}

/** Normalize any price string for display (handles stale EUR from cache/API). */
export function normalizePriceDisplay(
  formatted: string | undefined,
  cents: number,
  currencyCode = 'ALL',
): string {
  if (cents > 0) {
    return formatPerkPrice(cents, currencyCode)
  }
  if (formatted && !/EUR|€/i.test(formatted)) {
    return formatted
  }
  return formatPerkPrice(cents, currencyCode)
}
