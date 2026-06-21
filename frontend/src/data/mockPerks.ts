import type { Perk } from '@/types'

export const MOCK_PERKS: Perk[] = [
  {
    id: 'perk-gym',
    name: 'Abonim palestre premium',
    category: 'fitness',
    short_description: 'Qasje e pakufizuar në 200+ palestra partner në të gjithë vendin.',
    employee_price_formatted: '45 lekë/muaj',
    employee_price_cents: 4500,
    tags: ['gym', 'fitness', 'unlimited'],
    recommendation_score: 0.92,
    reason_text: 'Përputhet me stilin tënd aktiv',
  },
  {
    id: 'perk-hsa',
    name: 'Kontribut shëndetësor nga punëdhënësi',
    category: 'finance',
    short_description: 'Punëdhënësi mbulon deri në 120 lekë në vit për kontribute shëndetësore.',
    employee_price_formatted: '120 lekë/vit',
    employee_price_cents: 12000,
    tags: ['health', 'tax-advantaged'],
    recommendation_score: 0.88,
    reason_text: 'Kursim i mirë tatimor për të ardhurat e tua',
  },
  {
    id: 'perk-meal',
    name: 'Program subvencion ushqimi',
    category: 'food',
    short_description: '30 lekë kredi mujore për partnerë dërgese ushqimi të shëndetshëm.',
    employee_price_formatted: '30 lekë/muaj',
    employee_price_cents: 3000,
    tags: ['food', 'delivery', 'wellness'],
    recommendation_score: 0.85,
    reason_text: 'Plotëson prioritetin tënd për mirëqenie',
  },
  {
    id: 'perk-yoga',
    name: 'Abonim studio joga',
    category: 'wellness',
    short_description: 'Klasa të pakufizuara në 50+ studio në qytet.',
    employee_price_formatted: '45 lekë/muaj',
    employee_price_cents: 4500,
    tags: ['yoga', 'wellness', 'flexible'],
    recommendation_score: 0.87,
    reason_text: 'Prioritet i lartë mirëqenie në profilin tënd',
  },
  {
    id: 'perk-bike',
    name: 'Abonim vjetor biçikleta',
    category: 'transport',
    short_description: 'Anëtarësim biçikletash për komutimin tënd.',
    employee_price_formatted: '15 lekë/muaj',
    employee_price_cents: 1500,
    tags: ['transport', 'cycling', 'commute'],
    recommendation_score: 0.78,
    reason_text: 'I përshtatshëm për komutimin me biçikletë',
  },
  {
    id: 'perk-meditation',
    name: 'Headspace Premium',
    category: 'wellness',
    short_description: 'Qasje e plotë në meditim dhe përmbajtje për gjumë.',
    employee_price_formatted: '12 lekë/muaj',
    employee_price_cents: 1200,
    tags: ['meditation', 'mental-health', 'digital'],
    recommendation_score: 0.82,
    reason_text: 'Ndihmon me menaxhimin e stresit',
  },
  {
    id: 'perk-language',
    name: 'Kurse gjuhësh profesionale',
    category: 'education',
    short_description: 'Kurse gjuhësh me tutor live.',
    employee_price_formatted: '25 lekë/muaj',
    employee_price_cents: 2500,
    tags: ['education', 'language', 'career'],
    recommendation_score: 0.65,
    reason_text: 'Për zhvillim karriere',
  },
  {
    id: 'perk-travel',
    name: 'Sigurim udhëtimi Plus',
    category: 'travel',
    short_description: 'Mbulim udhëtimi për punë dhe pushime.',
    employee_price_formatted: '18 lekë/muaj',
    employee_price_cents: 1800,
    tags: ['travel', 'insurance', 'family'],
    recommendation_score: 0.71,
    reason_text: 'Mbulim udhëtimi për familjen',
  },
]

export const RECOMMENDED_PERK_IDS = ['perk-gym', 'perk-hsa', 'perk-meal']

export function getRecommendedPerks(): Perk[] {
  return RECOMMENDED_PERK_IDS.map((id) => MOCK_PERKS.find((p) => p.id === id)!).filter(Boolean)
}

export const CATEGORIES = [
  'all',
  'fitness',
  'wellness',
  'food',
  'travel',
  'transport',
  'finance',
] as const
export type CategoryFilter = (typeof CATEGORIES)[number]
