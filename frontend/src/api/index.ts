import { api } from '@/lib/api'
import type { ForgeStatusResponse, ForgeHistoryItem, PlanetSummary, PlanetDetail, RankingEntry } from '@/types'

export const forgeApi = {
  start:   (ship_a_id: string, ship_b_id: string) => api.post<ForgeStatusResponse>('/forge', { ship_a_id, ship_b_id }),
  status:  (id: string)                           => api.get<ForgeStatusResponse>(`/forge/${id}`),
  history: ()                                     => api.get<ForgeHistoryItem[]>('/forge/history'),
}

export const planetsApi = {
  list: ()           => api.get<PlanetSummary[]>('/planets'),
  get:  (id: string) => api.get<PlanetDetail>(`/planets/${id}`),
}

export const rankingApi = {
  list:  (limit = 100) => api.get<RankingEntry[]>(`/ranking?limit=${limit}`),
  me:    ()             => api.get<{ rank: number; player_id: string; username: string; score: number }>('/ranking/me'),
}

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  player_id: string
  username: string
}

export const authApi = {
  register: (username: string, email: string, password: string) =>
    api.post<TokenResponse>('/auth/register', { username, email, password }),
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),
}
