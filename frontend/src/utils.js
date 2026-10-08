import { typeLabel, statusLabel, PAYMENT_TYPES } from './constants'

export function fmtDate(d) {
  if (!d) return '-'
  const x = new Date(d.length === 10 ? d + 'T00:00:00' : d)
  if (isNaN(x)) return d
  return x.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtDateTime(d) {
  if (!d) return '-'
  const x = new Date(d)
  return x.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export const money = (v) => 'Rs. ' + Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function isoDate(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export function getPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? o : o[k]), obj)
}

export function formatCell(value, kind) {
  if (value === null || value === undefined || value === '') return '-'
  if (kind === 'date') return fmtDate(value)
  if (kind === 'datetime') return fmtDateTime(value)
  if (kind === 'money') return money(value)
  if (kind === 'type') return typeLabel(value)
  if (kind === 'ptype') return PAYMENT_TYPES[value] || value
  if (kind === 'status') return statusLabel(value)
  if (kind === 'bool') return value ? 'Yes' : 'No'
  return value
}

export function exportCsv(filename, columns, rows) {
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = [columns.map((c) => esc(c.label)).join(',')]
  rows.forEach((r) => lines.push(columns.map((c) => esc(formatCell(getPath(r, c.key), c.kind))).join(',')))
  // BOM so Excel shows Sinhala / Tamil text correctly
  const blob = new Blob(['\ufeff' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename + '.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

// Make a chosen photo smaller in the browser before uploading; returns a JPEG data URL.
export function shrinkImage(file, maxW, maxH) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, maxW / img.width, maxH / img.height)
      const c = document.createElement('canvas')
      c.width = Math.round(img.width * scale)
      c.height = Math.round(img.height * scale)
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height)
      URL.revokeObjectURL(img.src)
      resolve(c.toDataURL('image/jpeg', 0.85))
    }
    img.onerror = () => reject(new Error('This file is not a picture. Please choose a JPG or PNG photo.'))
    img.src = URL.createObjectURL(file)
  })
}

export function openPrint(path) {
  window.open(path, '_blank', 'width=900,height=700')
}
