import { api } from '@/lib/api'
import type {
  ShipSummary, ShipDetail, BuildShipRequest, BuildShipResponse,
  InstallModuleRequest, CurrentStats,
} from '@/types'
import type { PlayerModule } from '@/types'

export const shipsApi = {
  list:    ()                      => api.get<ShipSummary[]>('/ships'),
  get:     (id: string)            => api.get<ShipDetail>(`/ships/${id}`),
  build:   (req: BuildShipRequest) => api.post<BuildShipResponse>('/ships/build', req),
  demolish: (id: string)           => api.delete<void>(`/ships/${id}`),

  modules: {
    list:    (shipId: string)                                => api.get<PlayerModule[]>(`/ships/${shipId}/modules`),
    install: (shipId: string, slot: number, req: InstallModuleRequest) =>
      api.put<{ current_stats: CurrentStats; cap_reached: string[] }>(`/ships/${shipId}/modules/${slot}`, req),
    remove:  (shipId: string, slot: number)                  =>
      api.delete<{ destroyed: boolean }>(`/ships/${shipId}/modules/${slot}`),
  },

  scars:    (shipId: string) => api.get<Array<{ scar_id: string; tag_code: string; narrative: string; earned_at: string }>>(`/ships/${shipId}/scars`),
  missions: (shipId: string) => api.get<unknown[]>(`/ships/${shipId}/missions`),
}
