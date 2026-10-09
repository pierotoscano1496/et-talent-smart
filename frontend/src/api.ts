export type Account = { id: number; email: string; name: string; role: string }
let token: string | null = null
let account: Account | null = null
export const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', 'Bearer ' + token)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(apiBase + path, { ...options, headers })
  if (response.status === 401 && token) {
    token = null
    account = null
    window.dispatchEvent(new Event('session-expired'))
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'No se pudo completar la operación.')
  }
  return response.status === 204 ? undefined as T : response.json()
}

export async function login(email: string, password: string) {
  const result = await request<{ token: string; user: Account }>('/api/auth/login/', {
    method: 'POST', body: JSON.stringify({ email, password }),
  })
  token = result.token
  account = result.user
}
export function currentAccount() { return account }
export async function logout() {
  try { await request('/api/auth/logout/', { method: 'POST' }) }
  finally { token = null; account = null }
}
export async function downloadAttendance(query: string) {
  const response = await fetch(apiBase + '/api/attendance/export/' + query, {
    headers: { Authorization: 'Bearer ' + token },
  })
  if (!response.ok) throw new Error('No se pudo descargar el reporte.')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'asistencias.csv'
  link.click()
  URL.revokeObjectURL(url)
}

