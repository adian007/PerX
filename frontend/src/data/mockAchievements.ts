import type { Achievement } from '@/types'

export const ACHIEVEMENTS: Achievement[] = [
  {
    slug: 'first-steps',
    title: 'Hapat e parë',
    description: 'Përfundo hapin e parë të rrugës së përfitimeve.',
    requirement: 'Përfundo çdo milestone udhëtimi',
    unlocked: true,
    unlockedAt: '2025-06-01',
  },
  {
    slug: 'globe-trotter',
    title: 'Eksplorues global',
    description: 'Eksploro përfitime në 4 kategori të ndryshme.',
    requirement: 'Vizito 4 kategori në Eksploro',
    unlocked: false,
  },
  {
    slug: 'wishlist-curator',
    title: 'Kurues i të ruajturave',
    description: 'Shto 5 përfitime te të ruajturat.',
    requirement: '5 artikuj të ruajtur',
    unlocked: false,
  },
  {
    slug: 'smart-spender',
    title: 'Zgjedhës i zgjuar',
    description: 'Zgjidh një përfitim me bonus pyetësorë.',
    requirement: 'Përfundo rrjedhën Pyetësorë + Zgjidh',
    unlocked: false,
  },
  {
    slug: 'well-rounded',
    title: 'I balancuar',
    description: 'Përfundo të gjitha hapat e rrugës.',
    requirement: 'Të 4 hapat e rrugës',
    unlocked: false,
  },
  {
    slug: 'budget-master',
    title: 'Mjeshtër buxheti',
    description: 'Mbaj përdorimin e buxhetit nën 80% për 3 muaj.',
    requirement: '3 muaj nën 80%',
    unlocked: false,
  },
  {
    slug: 'marathoner',
    title: 'Maratonist',
    description: 'Regjistro 100 km aktiv drejt objektivit të fitnessit.',
    requirement: '100 km të regjistruara',
    unlocked: false,
    interactive: true,
    progress: 0,
    goal: 100,
  },
]
