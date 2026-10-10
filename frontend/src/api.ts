export type Account = { id: number; email: string; name: string; role: string }
let token: string | null = null
let account: Account | null = null
export const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const sessionToken = token
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', 'Bearer ' + token)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(apiBase + path, { ...options, headers })
  if (response.status === 401 && sessionToken && token === sessionToken) {
    token = null
    account = null
    window.dispatchEvent(new Event('session-expired'))
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const describe = (value: unknown): string => {
      if (typeof value === 'string') return value
      if (Array.isArray(value)) return value.map(describe).join(' ')
      if (value && typeof value === 'object') {
        const labels: Record<string, string> = { email: 'Correo', password: 'Contraseña', first_name: 'Nombres', last_name: 'Apellidos', role: 'Rol', rfid_uid: 'Llave RFID', classroom: 'Grado y sección', children: 'Hijos', draft: 'Borrador', teacher: 'Docente', start: 'Inicio', end: 'Fin', non_field_errors: '' }
        return Object.entries(value).map(([key, item]) => `${labels[key] ?? key}${labels[key] === '' ? '' : ': '}${describe(item)}`).join(' ')
      }
      return ''
    }
    throw new Error(describe(error.detail || error) || 'No se pudo completar la operación.')
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

export async function listAll<T>(path: string): Promise<T[]> {
  const results: T[] = []
  let next: string | null = path
  while (next) {
    const page: { results: T[]; next: string | null } = await request(next)
    results.push(...page.results)
    if (page.next) {
      const url = new URL(page.next, apiBase)
      next = url.pathname + url.search
    } else next = null
  }
  return results
}
export async function logout() {
  try { await request('/api/auth/logout/', { method: 'POST' }) }
  finally { token = null; account = null }
}
export async function downloadAttendance(query: string) {
  const sessionToken = token
  const response = await fetch(apiBase + '/api/attendance/export/' + query, {
    headers: { Authorization: 'Bearer ' + token },
  })
  if (response.status === 401 && sessionToken && token === sessionToken) {
    token = null
    account = null
    window.dispatchEvent(new Event('session-expired'))
  }
  if (!response.ok) throw new Error('No se pudo descargar el reporte.')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'asistencias.csv'
  link.click()
  URL.revokeObjectURL(url)
}

