import { api } from '@/lib/api'
import type { PlayerModule, LootCrate, LootCrateOpenResult } from '@/types'

export interface ShardCountOut {
  shards: Record<string, number>
}

export interface CraftModuleRequest {
  module_ids: string[]
  planet_id: string
}

export const modulesApi = {
  inventory: ()                          => api.get<PlayerModule[]>('/modules'),
  shards:    ()                          => api.get<ShardCountOut>('/modules/shards'),
  craft:     (req: CraftModuleRequest)   => api.post<PlayerModule>('/modules/craft', req),

  crates: {
    list: ()               => api.get<LootCrate[]>('/loot-crates'),
    open: (id: string)     => api.post<LootCrateOpenResult>(`/loot-crates/${id}/open`, {}),
  },
}
