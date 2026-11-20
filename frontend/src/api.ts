export const fmt = (value: number | null | undefined, digits = 1) =>
  value == null || !Number.isFinite(value)
    ? '—'
    : value.toLocaleString(undefined, { maximumFractionDigits: digits })

export class ApiError extends Error {
  detail: unknown

  constructor(message: string, detail: unknown) {
    super(message)
    this.detail = detail
  }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    let detail: unknown
    try {
      const body = await response.json()
      detail = body.detail
      message = describeApiError(body.detail) || body.message || message
    } catch {
      /* keep status */
    }
    if (response.status === 401 || response.status === 403) {
      const reason = response.status === 401 ? 'Authentication required' : 'Access denied'
      throw new Error(`${reason}. Ask the administrator to check access through the API proxy.`)
    }
    throw new ApiError(message, detail)
  }
  return response.json() as Promise<T>
}

function describeApiError(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((entry) => {
      if (typeof entry === 'string') return entry
      if (!entry || typeof entry !== 'object') return String(entry)
      const item = entry as { loc?: unknown[]; msg?: unknown }
      const location = Array.isArray(item.loc) ? item.loc.map(String).join(' → ') : ''
      return [location, typeof item.msg === 'string' ? item.msg : 'Invalid value']
        .filter(Boolean)
        .join(': ')
    })
    return messages.join('; ')
  }
  if (detail && typeof detail === 'object') {
    const item = detail as { msg?: unknown; message?: unknown }
    return typeof item.msg === 'string'
      ? item.msg
      : typeof item.message === 'string'
        ? item.message
        : JSON.stringify(detail)
  }
  return null
}
