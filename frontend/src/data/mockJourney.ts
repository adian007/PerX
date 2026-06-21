import type { JourneyNode } from '@/types'

export const JOURNEY_PATH =
  'M 120 240 Q 200 160 320 190 Q 420 210 520 170 Q 600 140 700 120'

export const JOURNEY_NODES: JourneyNode[] = [
  {
    category: 'food',
    label: 'Ushqim',
    status: 'current',
    affinityScore: 0.55,
    perkCount: 67,
    reasonText:
      'Subvencione ushqimi dhe dërgesa. Fillo këtu për të parë si funksionojnë.',
    x: 120,
    y: 240,
  },
  {
    category: 'fitness',
    label: 'Fitness',
    status: 'available',
    affinityScore: 0.75,
    perkCount: 42,
    reasonText: 'Karta palestre dhe përfitime fitness. Përfundo Ushqimin fillimisht.',
    x: 320,
    y: 190,
  },
  {
    category: 'wellness',
    label: 'Mirëqenie',
    status: 'available',
    affinityScore: 0.8,
    perkCount: 31,
    reasonText: 'Joga, meditim dhe shëndet mendor. Hapet pasi të mbarosh hapat e mëparshëm.',
    x: 520,
    y: 170,
  },
  {
    category: 'travel',
    label: 'Udhëtim',
    status: 'locked',
    affinityScore: 0.15,
    perkCount: 8,
    reasonText: 'Hapet në nivelin 4. Sigurim udhëtimi dhe transport.',
    x: 700,
    y: 120,
  },
]

export const AI_TIP =
  'Rruga fillon me Ushqimin. Përfundo pyetësorin për të shënuar çdo hap dhe hap kategorinë tjetër.'
