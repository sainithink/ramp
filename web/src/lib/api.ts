/** Thin wrappers over the FastAPI routes in core/routes.py. */

export type Me = {
  id: string
  email: string
  display_name: string
  wake_name: string
  role: 'user' | 'admin'
  plan: string
  used: number
  limit: number
  remaining: number
}

export type AdminUser = {
  id: string
  email: string
  display_name: string
  wake_name: string
  role: 'user' | 'admin'
  plan: string
  is_active: boolean
  used: number
  limit: number
  total: number
  custom_limit: number | null
  created_at: string | null
  last_seen_at: string | null
}

export type AdminPayload = {
  stats: {
    total_users: number
    active_users: number
    admins: number
    conversations_this_month: number
  }
  plans: Record<string, number>
  users: AdminUser[]
}

/** Raised for a non-2xx response, carrying the server's own message. */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: init?.body
      ? { 'Content-Type': 'application/json', ...init?.headers }
      : init?.headers,
  })
  const data = await res.json().catch(() => ({}) as Record<string, unknown>)
  if (!res.ok) {
    throw new ApiError(res.status, (data as { detail?: string }).detail || 'Something went wrong.')
  }
  return data as T
}

export const api = {
  me: () => request<Me>('/api/me'),

  login: (email: string, password: string) =>
    request<{ id: string; role: string }>('/api/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, wake_name: string, display_name: string) =>
    request<{ id: string; role: string }>('/api/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, wake_name, display_name }),
    }),

  logout: () => request<{ ok: boolean }>('/api/logout', { method: 'POST' }),

  setWakeName: (wake_name: string) =>
    request<{ wake_name: string }>('/api/me/wake-name', {
      method: 'POST',
      body: JSON.stringify({ wake_name }),
    }),

  adminUsers: () => request<AdminPayload>('/api/admin/users'),

  adminUpdate: (id: string, body: Record<string, unknown>) =>
    request<Partial<AdminUser>>(`/api/admin/users/${id}`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}

/**
 * The same rules as core/auth.validate_wake_name, so a bad name is caught
 * before the round trip. The server still has the last word.
 */
export function checkWakeName(raw: string): { ok: true; name: string } | { ok: false; why: string } {
  const n = (raw || '').trim()
  if (!n) return { ok: true, name: 'Saira' }
  if (n.length > 24) return { ok: false, why: 'Too long — 24 characters max.' }
  if (!/^[A-Za-z ]+$/.test(n)) return { ok: false, why: 'Letters only.' }
  if (n.split(/\s+/).length > 1) return { ok: false, why: 'Use a single word so it can be heard reliably.' }
  if (n.length < 3) return { ok: false, why: 'At least 3 letters — shorter names trigger on ordinary speech.' }
  return { ok: true, name: n.charAt(0).toUpperCase() + n.slice(1).toLowerCase() }
}
