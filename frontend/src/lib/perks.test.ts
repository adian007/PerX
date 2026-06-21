import { describe, expect, it } from 'vitest'
import { formatPerkPrice, mapApiPerk, normalizePriceDisplay } from '@/lib/perks'

describe('formatPerkPrice', () => {
  it('returns included label for zero cents', () => {
    expect(formatPerkPrice(0)).toBe('Përfshirë')
  })

  it('formats ALL amounts in Lek for sq-AL locale', () => {
    expect(formatPerkPrice(4500, 'ALL')).toBe('45 Lek')
    expect(formatPerkPrice(125000, 'ALL')).toBe('1.250 Lek')
  })

  it('formats EUR with symbol', () => {
    expect(formatPerkPrice(1999, 'EUR', 'en')).toBe('€19.99')
  })
})

describe('mapApiPerk', () => {
  it('maps API perk fields to UI perk shape', () => {
    const perk = mapApiPerk({
      id: 'abc',
      name: 'Yoga Studio',
      category: 'wellness',
      short_description: 'Monthly pass',
      employee_price_formatted: '45 Lek',
      employee_price_cents: 4500,
      tags: ['yoga'],
    })

    expect(perk.id).toBe('abc')
    expect(perk.name).toBe('Yoga Studio')
    expect(perk.employee_price_formatted).toBe('45 Lek')
    expect(perk.tags).toEqual(['yoga'])
  })
})

describe('normalizePriceDisplay', () => {
  it('prefers cents-based formatting when cents are positive', () => {
    expect(normalizePriceDisplay('€45', 4500, 'ALL')).toBe('45 Lek')
  })

  it('keeps non-EUR formatted strings when cents are zero', () => {
    expect(normalizePriceDisplay('Përfshirë', 0, 'ALL')).toBe('Përfshirë')
  })
})
