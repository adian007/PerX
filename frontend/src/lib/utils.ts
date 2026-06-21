import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { greeting as i18nGreeting } from '@/i18n'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPoints(n: number): string {
  return n.toLocaleString('sq-AL')
}

export function getGreeting(name: string): string {
  return i18nGreeting(name)
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
