// Change these lists here if the library adds new types or sections.
export const MEMBERSHIP_TYPES = [
  { value: 'CHILD', label: 'Child' },
  { value: 'STUDENT', label: 'Student' },
  { value: 'ADULT', label: 'Adult' },
  { value: 'LIFETIME', label: 'Life Time' },
]

export const SECTIONS = ['Lending', 'Children', 'Buddhist', 'Reference']

export const BOOK_STATUS = {
  AVAILABLE: { label: 'In library', cls: 'green' },
  ISSUED: { label: 'Issued', cls: 'orange' },
  DAMAGED: { label: 'Damaged', cls: 'red' },
  LOST: { label: 'Lost', cls: 'red' },
  WITHDRAWN: { label: 'Withdrawn', cls: 'gray' },
}

export const PAYMENT_TYPES = {
  ISSUE_FEE: 'Book issue fee',
  LATE_FINE: 'Late return fine',
  DAMAGE_FINE: 'Damaged book charge',
  LOST_FINE: 'Missing book charge',
  FINE: 'Book charges (more than one)',
  MEMBERSHIP: 'Membership fee',
  OTHER: 'Other',
}

export const typeLabel = (v) => MEMBERSHIP_TYPES.find((t) => t.value === v)?.label || v || '-'
export const statusLabel = (v) => BOOK_STATUS[v]?.label || v
