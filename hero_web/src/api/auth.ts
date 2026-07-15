import { apiClient, clearStoredToken, setStoredToken } from '@/api/client'
import type { RegisterPayload, TokenResponse, User } from '@/types/auth'

export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)

  const { data } = await apiClient.post<TokenResponse>('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  setStoredToken(data.access_token)
  return data
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await apiClient.post<User>('/auth/register', payload)
  return data
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me')
  return data
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post('/auth/logout')
  } finally {
    clearStoredToken()
  }
}
