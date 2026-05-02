import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  playerId: string | null
  username: string | null
  setTokens: (access: string, refresh: string) => void
  setPlayerId: (id: string, username?: string) => void
  logout: () => void
  isAuthenticated: () => boolean
  initialize: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken:  null,
      refreshToken: null,
      playerId:     null,
      username:     null,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      setPlayerId: (id, username) =>
        set({ playerId: id, username: username ?? null }),

      logout: () =>
        set({ accessToken: null, refreshToken: null, playerId: null, username: null }),

      isAuthenticated: () => !!get().accessToken,

      initialize: async () => {
        const { refreshToken, setTokens, logout } = get()
        if (!refreshToken) return
        try {
          const res = await fetch('/api/v1/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          })
          if (!res.ok) { logout(); return }
          const data = await res.json()
          setTokens(data.access_token, data.refresh_token)
        } catch {
          logout()
        }
      },
    }),
    {
      name: 'emago-auth',
      // Persiste uniquement le refresh token (l'access token est volatile)
      partialize: (state) => ({
        refreshToken: state.refreshToken,
        playerId:     state.playerId,
        username:     state.username,
      }),
    },
  ),
)
