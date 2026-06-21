import { describe, expect, it } from 'vitest'
import {
  categoryLabel,
  greeting,
  perkCountLabel,
  t,
  tf,
} from '@/i18n'

describe('i18n t()', () => {
  it('returns Albanian strings for known keys', () => {
    expect(t('common.loading')).toBe('Duke u ngarkuar…')
    expect(t('nav.home')).toBe('Kryefaqja')
  })

  it('falls back to the key when missing', () => {
    expect(t('missing.key.path')).toBe('missing.key.path')
  })
})

describe('i18n tf()', () => {
  it('interpolates template functions from sq-AL', () => {
    expect(tf('journey.reasonCompleted', 'ushqim', '85')).toContain('85%')
    expect(tf('journey.reasonCompleted', 'ushqim', '85')).toContain('ushqim')
  })
})

describe('i18n helpers', () => {
  it('formats perk counts in Albanian', () => {
    expect(perkCountLabel(1)).toBe('1 përfitim')
    expect(perkCountLabel(3)).toBe('3 përfitime')
  })

  it('labels known categories', () => {
    expect(categoryLabel('fitness')).toBe('Fitness')
    expect(categoryLabel('wellness')).toBe('Mirëqenie')
  })

  it('builds a greeting with an optional name', () => {
    const result = greeting('Ana')
    expect(result).toContain('Ana')
    expect(result.length).toBeGreaterThan(3)
  })
})
