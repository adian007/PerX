import { sqAL } from './sq-AL'

export const DEFAULT_LOCALE = 'sq-AL'

type NestedStrings = { [key: string]: string | NestedStrings | ((...args: string[]) => string) }

function getNested(obj: NestedStrings, path: string): string | undefined {
  const parts = path.split('.')
  let cur: unknown = obj
  for (const part of parts) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = (cur as NestedStrings)[part]
  }
  return typeof cur === 'string' ? cur : undefined
}

function getNestedFn(obj: NestedStrings, path: string): ((...args: string[]) => string) | undefined {
  const parts = path.split('.')
  let cur: unknown = obj
  for (const part of parts) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = (cur as NestedStrings)[part]
  }
  return typeof cur === 'function' ? (cur as (...args: string[]) => string) : undefined
}

/** Translate a dot-path key; falls back to the key if missing. */
export function t(path: string): string {
  return getNested(sqAL as NestedStrings, path) ?? path
}

export function tf(path: string, ...args: string[]): string {
  const fn = getNestedFn(sqAL as NestedStrings, path)
  return fn ? fn(...args) : path
}

export function greeting(name: string): string {
  const hour = new Date().getHours()
  const base =
    hour < 12
      ? t('home.greetingMorning')
      : hour < 17
        ? t('home.greetingAfternoon')
        : t('home.greetingEvening')
  return name ? `${base}, ${name}` : base
}

export function categoryLabel(category: string): string {
  return t(`categories.${category}`) !== `categories.${category}`
    ? t(`categories.${category}`)
    : category.charAt(0).toUpperCase() + category.slice(1)
}

export function levelLabel(level: number): string {
  return t(`levels.${level}`) !== `levels.${level}`
    ? t(`levels.${level}`)
    : tf('common.levelFallback', String(level))
}

export function perkCountLabel(count: number): string {
  return count === 1 ? t('common.perkCountOne') : `${count} ${t('common.perkCountMany')}`
}

export function journeyReasonCompleted(label: string, pct: number): string {
  return tf('journey.reasonCompleted', label.toLowerCase(), String(pct))
}

export function journeyReasonCurrent(label: string, pct: number, count: number): string {
  return tf('journey.reasonCurrent', label.toLowerCase(), String(pct), perkCountLabel(count))
}

export function journeyReasonAvailable(label: string, pct: number, count: number): string {
  return tf('journey.reasonAvailable', label, String(pct), perkCountLabel(count))
}

export function journeyAiTipCurrent(label: string, pct: number, count: number): string {
  return tf('journey.aiTipCurrent', label.toLowerCase(), String(pct), perkCountLabel(count))
}

export function journeyAiTipTop(category: string, pct: number): string {
  return tf('journey.aiTipTop', categoryLabel(category).toLowerCase(), String(pct))
}
