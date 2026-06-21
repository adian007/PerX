import type { Variants } from 'framer-motion'

export const LANDING_SECTIONS = [
  { id: 'vision', label: 'Vision', step: '01' },
  { id: 'ecosystem', label: 'Ecosystem', step: '02' },
  { id: 'network', label: 'Network', step: '03' },
  { id: 'origin', label: 'Origin', step: '04' },
] as const

export type LandingSectionId = (typeof LANDING_SECTIONS)[number]['id']

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.94 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.65, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export const slideFromLeft: Variants = {
  hidden: { opacity: 0, x: -32 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export const slideFromRight: Variants = {
  hidden: { opacity: 0, x: 32 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export const stagger: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.12, delayChildren: 0.06 },
  },
}

export const staggerFast: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.08, delayChildren: 0.04 },
  },
}

export function sectionViewport(reducedMotion: boolean | null) {
  return {
    once: true as const,
    amount: 0.25,
    ...(reducedMotion ? {} : {}),
  }
}

export function sectionInitial(reducedMotion: boolean | null) {
  return reducedMotion ? false : ('hidden' as const)
}
