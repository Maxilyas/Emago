/**
 * Client API Emago.
 * - Injecte automatiquement le header Authorization
 * - Gère le refresh token silencieux sur 401
 * - Lève des erreurs typées exploitables dans les composants
 */
import { useAuthStore } from '@/stores/authStore'

const BASE_URL = '/api/v1'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

async function refreshToken(): Promise<boolean> {
  const store = useAuthStore.getState()
  const rt = store.refreshToken
  if (!rt) return false

  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    if (!res.ok) return false
    const data = await res.json()
    store.setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const { accessToken, logout } = useAuthStore.getState()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  // Refresh silencieux sur 401
  if (res.status === 401 && retry) {
    const ok = await refreshToken()
    if (ok) return request<T>(path, options, false)
    logout()
    throw new ApiError(401, 'Session expirée')
  }

  if (res.status === 204) return undefined as unknown as T

  const json = await res.json().catch(() => ({ detail: res.statusText }))

  if (!res.ok) {
    throw new ApiError(res.status, json.detail ?? 'Erreur serveur')
  }

  return json as T
}

// Helpers
export const api = {
  get:    <T>(path: string)                       => request<T>(path),
  post:   <T>(path: string, body: unknown)        => request<T>(path, { method: 'POST',   body: JSON.stringify(body) }),
  put:    <T>(path: string, body: unknown)        => request<T>(path, { method: 'PUT',    body: JSON.stringify(body) }),
  patch:  <T>(path: string, body: unknown)        => request<T>(path, { method: 'PATCH',  body: JSON.stringify(body) }),
  delete: <T>(path: string)                       => request<T>(path, { method: 'DELETE' }),
}
