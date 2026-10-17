// Payment lines -> receipts. One receipt can hold several books, and (for a group visit:
// family, friends) several members. Each line still belongs to its own member.

// The lines of one member on a receipt
function memberPart(lines) {
  const first = lines[0]
  return {
    member_id: first.member_id, member_name: first.member_name, member_no: first.member_no,
    lines, total: lines.reduce((t, p) => t + Number(p.amount), 0),
  }
}

// One receipt from all its lines
export function toReceipt(lines) {
  const first = lines[0]
  const byMember = new Map()
  for (const p of lines) {
    if (!byMember.has(p.member_id)) byMember.set(p.member_id, [])
    byMember.get(p.member_id).push(p)
  }
  const members = [...byMember.values()].map(memberPart)
  return {
    receipt_no: first.receipt_no, id: first.id, paid_at: first.paid_at, received_by: first.received_by,
    lines, members, isGroup: members.length > 1,
    total: lines.reduce((t, p) => t + Number(p.amount), 0),
    types: [...new Set(lines.map((p) => p.payment_type))],
    refs: [...new Set(lines.map((p) => p.ref).filter(Boolean))].join(', '),
    // the first member, for a one-member receipt (most receipts)
    member_id: first.member_id, member_name: first.member_name, member_no: first.member_no,
  }
}

// Many payment lines -> one receipt per receipt number, in the order first seen
export function groupReceipts(lines) {
  const byNo = new Map()
  for (const p of lines) {
    if (!byNo.has(p.receipt_no)) byNo.set(p.receipt_no, [])
    byNo.get(p.receipt_no).push(p)
  }
  return [...byNo.values()].map(toReceipt)
}

// "Nimal Perera + 2 more" for a group receipt, the member's name otherwise
export function whoPaid(r) {
  return r.isGroup ? `${r.members[0].member_name} + ${r.members.length - 1} more` : r.member_name
}
