const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type ApiOptions = RequestInit & { token?: string }

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {})
  headers.set('Content-Type', 'application/json')
  if (options.token) {
    headers.set('Authorization', `******
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = 'Request failed.'
    try {
      const data = await response.json()
      message = data.detail ?? message
    } catch {
      // ignore json parse failure
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
