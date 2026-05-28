import { VisitType } from '@/types/domain'

export interface VisitSlotConfig {
  visitType: VisitType
  label: string
  group: 'prenatal' | 'labor' | 'postnatal'
  ocrPageType: 'prenatal' | 'birth'
  isLabor: boolean
}

export const VISIT_SLOTS: VisitSlotConfig[] = [
  { visitType: 'prenatal_1', label: 'Prenatal 1', group: 'prenatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'prenatal_2', label: 'Prenatal 2', group: 'prenatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'prenatal_3', label: 'Prenatal 3', group: 'prenatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'prenatal_4', label: 'Prenatal 4', group: 'prenatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'prenatal_5', label: 'Prenatal 5', group: 'prenatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'prenatal_6', label: 'Prenatal 6', group: 'prenatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'labor',      label: 'Labor',      group: 'labor',    ocrPageType: 'birth',    isLabor: true  },
  { visitType: 'postnatal_1', label: 'Postnatal 1', group: 'postnatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'postnatal_2', label: 'Postnatal 2', group: 'postnatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'postnatal_3', label: 'Postnatal 3', group: 'postnatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'postnatal_4', label: 'Postnatal 4', group: 'postnatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'postnatal_5', label: 'Postnatal 5', group: 'postnatal', ocrPageType: 'prenatal', isLabor: false },
  { visitType: 'postnatal_6', label: 'Postnatal 6', group: 'postnatal', ocrPageType: 'prenatal', isLabor: false },
]

export const VISIT_GROUPS: { key: 'prenatal' | 'labor' | 'postnatal'; label: string }[] = [
  { key: 'prenatal',  label: 'Prenatal Visits' },
  { key: 'labor',     label: 'Labor' },
  { key: 'postnatal', label: 'Postnatal Visits' },
]

export function getSlotConfig(visitType: string): VisitSlotConfig | undefined {
  return VISIT_SLOTS.find((s) => s.visitType === visitType)
}
