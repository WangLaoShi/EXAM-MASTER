import { create } from 'zustand'
import { clearStoredToken, getStoredToken, setStoredToken } from '@/api/client'
import { fetchCurrentUser, login as loginApi, logout as logoutApi } from '@/api/auth'
import type { User } from '@/types/auth'

interface AuthState {
  token: string | null
  user: User | null
  initialized: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  bootstrap: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getStoredToken(),
  user: null,
  initialized: false,

  login: async (username, password) => {
    const tokenResponse = await loginApi(username, password)
    setStoredToken(tokenResponse.access_token)
    const user = await fetchCurrentUser()
    set({ token: tokenResponse.access_token, user })
  },

  logout: async () => {
    await logoutApi()
    clearStoredToken()
    set({ token: null, user: null })
  },

  bootstrap: async () => {
    const token = get().token ?? getStoredToken()
    if (!token) {
      set({ initialized: true, token: null, user: null })
      return
    }
    try {
      const user = await fetchCurrentUser()
      set({ token, user, initialized: true })
    } catch {
      clearStoredToken()
      set({ token: null, user: null, initialized: true })
    }
  },
}))
