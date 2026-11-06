import { VisitType } from '@/types/domain'

export interface VisitSlotConfig {
  visitType: VisitType
  label: string
  group: 'prenatal' | 'labor' | 'postnatal' | 'crisis_loss'
  ocrPageType: 'soap_note' | 'birth'
  isLabor: boolean
  topics?: string[]
}

export const VISIT_SLOTS: VisitSlotConfig[] = [
  {
    visitType: 'prenatal_1', label: 'Prenatal 1', group: 'prenatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Birth Preferences and Plan (initial introduction)',
      'Postpartum Planning (intro — who is your support?)',
      'Resources (books, classes, community groups)',
      'Agency goals and visit schedule overview',
      'Questions and concerns from client',
    ],
  },
  {
    visitType: 'prenatal_2', label: 'Prenatal 2', group: 'prenatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Birth Preferences and Plan (developing details)',
      'Pain Management Techniques (overview)',
      'Postpartum Planning (support people, logistics)',
      'Review questions from Prenatal 1',
    ],
  },
  {
    visitType: 'prenatal_3', label: 'Prenatal 3', group: 'prenatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Comfort Measures and Positioning',
      'Newborn Care Basics (intro)',
      'Mental Health Check In',
      'Review birth preferences progress',
    ],
  },
  {
    visitType: 'prenatal_4', label: 'Prenatal 4', group: 'prenatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Breastfeeding and Lactation Support (intro)',
      'Newborn Care Basics (continued)',
      'Checklist for Baby (supplies, safe sleep)',
      'Postpartum Planning (childcare, leave, support)',
    ],
  },
  {
    visitType: 'prenatal_5', label: 'Prenatal 5', group: 'prenatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Birth preferences review (penultimate — any gaps?)',
      'Pain management options (finalize preferences)',
      'Mental Health Check In',
      'Comfort Measures review (practice together)',
    ],
  },
  {
    visitType: 'prenatal_6', label: 'Prenatal 6', group: 'prenatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Birth preferences review — FINAL sign-off',
      'Postpartum Planning (final logistics confirmed)',
      'Checklist for Baby — all items complete?',
      'Resources (final list; emergency contacts)',
      'Mental Health Check In',
      'Labor onset signs — when to call doula',
    ],
  },
  {
    visitType: 'labor', label: 'Labor', group: 'labor', ocrPageType: 'birth', isLabor: true,
    topics: [
      'Birth preferences — quick reference review',
      'Comfort Measures and Positioning',
      'Pain management options (apply preferences)',
      'Fluid intake and nourishment',
      'Emotional support and encouragement',
      'Communication with medical team',
      'Feeding: Colostrum — first attempt',
      'Signs of a Good Latch',
      'Newborn Care Basics (immediate)',
      'Mental Health Check In (after birth)',
      'Fluid intake for recovery',
      'Schedule Postnatal 1 visit',
    ],
  },
  {
    visitType: 'postnatal_1', label: 'Postnatal 1', group: 'postnatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Feeding: Colostrum (quantity, frequency)',
      'Signs of a Good Latch',
      'Fluid intake and nutrition for recovery',
      'Mental Health Check In',
      'Newborn Care Basics (diapering, cord, skin)',
      'Recovery support (rest, bleeding, pain)',
    ],
  },
  {
    visitType: 'postnatal_2', label: 'Postnatal 2', group: 'postnatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Feeding: Colostrum → transitional milk',
      'Signs of a Good Latch (reassess)',
      'Keeping Up Milk Supply',
      'Mental Health Check In',
      'Fluid intake and nutrition',
      'Recovery check (physical healing)',
    ],
  },
  {
    visitType: 'postnatal_3', label: 'Postnatal 3', group: 'postnatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Breastfeeding and Lactation Support',
      'Pumping (introduction — when and how)',
      'Keeping Up Milk Supply',
      'Self Care (intro — rest, nutrition, support)',
      'Mental Health Check In',
      'Signs of a Good Latch (ongoing check)',
    ],
  },
  {
    visitType: 'postnatal_4', label: 'Postnatal 4', group: 'postnatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Feeding: Pumping / Transitional → Mature milk',
      'Keeping Up Milk Supply',
      'Breastfeeding troubleshooting',
      'Self Care (ongoing — sleep, nutrition, support)',
      'Mental Health Check In',
    ],
  },
  {
    visitType: 'postnatal_5', label: 'Postnatal 5', group: 'postnatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Mental Health Check In (6-week formal screening)',
      'Birth Control Options',
      'Self Care (ongoing plan)',
      'Breastfeeding and Lactation Support',
      'Keeping Up Milk Supply',
      '6-week OB clearance status',
    ],
  },
  {
    visitType: 'postnatal_6', label: 'Postnatal 6', group: 'postnatal', ocrPageType: 'soap_note', isLabor: false,
    topics: [
      'Mental Health Check In (closing screen)',
      'Birth Control Options (confirm decision)',
      'Self Care (sustainable long-term plan)',
      'Resources (community, peer support, hotlines)',
      'Keeping Up Milk Supply (if still feeding)',
      'Care plan summary and discharge',
    ],
  },
  { visitType: 'crisis_loss_1', label: 'Crisis/Loss Visit 1', group: 'crisis_loss', ocrPageType: 'soap_note', isLabor: false },
  { visitType: 'crisis_loss_2', label: 'Crisis/Loss Visit 2', group: 'crisis_loss', ocrPageType: 'soap_note', isLabor: false },
]

export const VISIT_GROUPS: { key: 'prenatal' | 'labor' | 'postnatal'; label: string }[] = [
  { key: 'prenatal',  label: 'Prenatal Visits' },
  { key: 'labor',     label: 'Labor' },
  { key: 'postnatal', label: 'Postnatal Visits' },
]

export function getSlotConfig(visitType: string): VisitSlotConfig | undefined {
  return VISIT_SLOTS.find((s) => s.visitType === visitType)
}

export function getNextSlot(visitType: VisitType): VisitSlotConfig | null {
  const idx = VISIT_SLOTS.findIndex((s) => s.visitType === visitType)
  return idx !== -1 && idx + 1 < VISIT_SLOTS.length ? VISIT_SLOTS[idx + 1] : null
}

export function getPrevSlotInGroup(visitType: VisitType): VisitType | null {
  const current = getSlotConfig(visitType)
  if (!current || current.group === 'labor' || current.group === 'crisis_loss') return null
  const groupSlots = VISIT_SLOTS.filter((s) => s.group === current.group)
  const idx = groupSlots.findIndex((s) => s.visitType === visitType)
  if (idx <= 0) return null
  return groupSlots[idx - 1].visitType as VisitType
}
