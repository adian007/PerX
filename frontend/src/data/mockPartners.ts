export type PartnerCategory = 'fitness' | 'food' | 'wellness' | 'insurance'

export interface Partner {
  id: string
  name: string
  category: PartnerCategory
  location: string
  tagline: string
  perkOffer: string
  highlight?: string
  externalUrl?: string
}

export const PARTNER_CATEGORIES: Record<PartnerCategory, string> = {
  fitness: 'Fitness',
  food: 'Ushqim & gastronomi',
  wellness: 'Mirëqenie',
  insurance: 'Sigurime',
}

export const MOCK_PARTNERS: Partner[] = [
  {
    id: 'lotus-fitness',
    name: 'Lotus Fitness Gym',
    category: 'fitness',
    location: 'Bulevardi Zogu I, Tirana',
    tagline: '1% më mirë çdo ditë',
    perkOffer: 'Karta palestre për punonjësit, me qasje në bootcamp dhe aerobik.',
    highlight: '8.400+ anëtarë',
    externalUrl: 'https://www.instagram.com/lotusgym_fitness',
  },
  {
    id: 'vila-ferdinand',
    name: 'Vila Ferdinand',
    category: 'food',
    location: 'Tiranë',
    tagline: 'Gastronomi & dërgesa',
    perkOffer: 'Subvencione ushqimi dhe kredi dërgese për programe dreke në zyrë.',
    highlight: 'Dërgesë falas',
  },
  {
    id: 'golden-spa',
    name: 'Golden Spa Relax Blloku',
    category: 'wellness',
    location: 'Blloku, Tiranë',
    tagline: 'Masazh & spa profesional',
    perkOffer: 'Seanca spa me zbritje dhe paketa mirëqenieje për ekipe.',
    highlight: 'Vlerësim 4.6',
  },
  {
    id: 'sigal-insurance',
    name: 'SIGAL Insurance Group',
    category: 'insurance',
    location: 'Shqipëri',
    tagline: 'Zgjidh mbulimin që të duhet',
    perkOffer: 'Shëndet udhëtimi, aksidente dhe plane jetë+kursim përmes pagës.',
    highlight: 'Tarifa grupi punëdhënësi',
    externalUrl: 'https://www.sigal.al',
  },
]
