function token() {
  return localStorage.getItem('token') || ''
}

async function request(method, url, body, params) {
  let full = '/api' + url
  if (params) {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) qs.append(k, v)
    })
    const s = qs.toString()
    if (s) full += '?' + s
  }
  const headers = { 'Content-Type': 'application/json' }
  if (token()) headers.Authorization = 'Bearer ' + token()
  const res = await fetch(full, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (res.status === 401 && !url.startsWith('/auth/login')) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    throw new Error('Please log in again')
  }
  if (!res.ok) {
    let msg = 'Something went wrong. Please try again.'
    if (data && data.detail) {
      msg = typeof data.detail === 'string'
        ? data.detail
        : data.detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(', ')
    }
    throw new Error(msg)
  }
  return data
}

export const api = {
  get: (u, p) => request('GET', u, undefined, p),
  post: (u, b) => request('POST', u, b ?? {}),
  put: (u, b) => request('PUT', u, b),
  del: (u) => request('DELETE', u),
}

export const qrUrl = (text, size = 8) => `/api/codes/qr?text=${encodeURIComponent(text)}&size=${size}`
export const barcodeUrl = (text) => `/api/codes/barcode?text=${encodeURIComponent(text)}`
