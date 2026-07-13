import { fetchAuthSession } from 'aws-amplify/auth'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3333/api/v1'

async function getToken(): Promise<string> {
  const session = await fetchAuthSession()
  return session.tokens?.idToken?.toString() ?? ''
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken()

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(error.message || `Error ${res.status}`)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) => {
    if (params) {
      const entries = Object.entries(params).filter(
        ([, v]) => v !== '' && v != null,
      )
      const qs = new URLSearchParams(
        entries.map(([k, v]) => [k, String(v)]),
      ).toString()
      if (qs) path += `?${qs}`
    }
    return request<T>(path)
  },
  post: <T>(path: string, body: object) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: object) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
}
