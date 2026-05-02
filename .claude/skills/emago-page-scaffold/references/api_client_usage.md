# Utilisation `lib/api.ts` Emago

## Vue d'ensemble

`@/lib/api` expose un client HTTP qui :
- Préfixe les URLs avec `/api/v1`.
- Injecte automatiquement `Authorization: Bearer <accessToken>` depuis `useAuthStore`.
- Gère le **silent refresh** sur 401 (re-token via refresh, retry de la requête, logout sinon).
- Lance `ApiError(status, detail)` pour toute réponse non-2xx.

## API exposée

```ts
import { api, ApiError } from '@/lib/api';

await api.get<T>(path: string): Promise<T>
await api.post<T>(path: string, body: unknown): Promise<T>
await api.put<T>(path: string, body: unknown): Promise<T>
await api.delete<T>(path: string): Promise<T>
```

## Patterns

### Pattern 1 — TanStack Query

```ts
const { data, isLoading } = useQuery({
  queryKey: ['ships'],
  queryFn: () => api.get<ShipSummary[]>('/ships'),
  refetchInterval: 30_000,
});
```

### Pattern 2 — Mutation

```ts
const createMutation = useMutation({
  mutationFn: (body: BuildShipRequest) =>
    api.post<BuildShipResponse>('/ships/build', body),
  onSuccess: (data) => {
    qc.invalidateQueries({ queryKey: ['ships'] });
    toast.success('Vaisseau construit');
  },
  onError: (err: any) => {
    toast.error(err.detail ?? 'Erreur');
  },
});

// Trigger :
createMutation.mutate({ ship_type: 'frigate_attack', planet_id: '...' });
```

### Pattern 3 — Wrapper API namespace

`@/api/index.ts` et `@/api/ships.ts` exposent des wrappers de plus haut niveau :

```ts
import { shipsApi, forgeApi, planetsApi, rankingApi, authApi } from '@/api';

// Usage typé :
const ships = await shipsApi.list();
const ship = await shipsApi.get(id);
await shipsApi.build({ ship_type, planet_id });
await shipsApi.demolish(id);
const modules = await shipsApi.modules.list(shipId);
await shipsApi.modules.install(shipId, slot, { module_type, level });
```

**Préférer ces wrappers** à `api.get('/ships/...')` direct dans les pages — meilleure découvrabilité, refacto plus simple.

### Pattern 4 — Gestion ApiError

```ts
try {
  const data = await api.post<T>('/x', body);
  return data;
} catch (err) {
  if (err instanceof ApiError) {
    if (err.status === 402) {
      toast.error('Ressources insuffisantes');
    } else if (err.status === 409) {
      toast.error('Action impossible : ' + err.detail);
    } else {
      toast.error(err.detail);
    }
  } else {
    toast.error('Erreur réseau');
  }
}
```

Avec TanStack Query, c'est plus simple :

```ts
mutation = useMutation({
  mutationFn: ...,
  onError: (err: any) => {
    if (err instanceof ApiError && err.status === 402) {
      toast.error('Pas assez de ressources');
    } else {
      toast.error(err.detail ?? 'Erreur serveur');
    }
  },
});
```

## Silent refresh sur 401

Géré automatiquement par `lib/api.ts`. Quand l'access token expire :

```
1. Requête → 401
2. lib/api.ts intercepte
3. POST /auth/refresh avec refreshToken (depuis useAuthStore)
4. Si succès → setTokens(new_access, new_refresh) + retry requête
5. Si échec → useAuthStore.logout() + ApiError(401, 'Session expirée')
```

Le composant ne voit ce 401 que si le refresh a échoué (cas rare : refresh token expiré ou révoqué).

## 204 No Content

`api.delete<T>('/ships/123')` retourne `undefined` quand le serveur renvoie 204. Toujours typer en `void` dans ce cas :

```ts
demolish: (id: string) => api.delete<void>(`/ships/${id}`),
```

## Conventions Emago

- ❌ Ne pas utiliser `fetch` ou `axios` direct — toujours `lib/api.ts`.
- ❌ Ne pas concaténer manuellement le préfixe `/api/v1` — déjà inclus.
- ❌ Ne pas gérer manuellement le header `Authorization` — `lib/api.ts` s'en occupe.
- ✅ Utiliser les wrappers `xxxApi` quand disponibles.
- ✅ Toujours typer les retours `<T>` pour la sécurité TypeScript.
- ✅ Utiliser `queryKey` cohérent : `['xxx']` pour list, `['xxx', id]` pour detail, `['xxx', { filter }]` pour filtré.

## Endpoints publics (sans auth)

Certains endpoints n'exigent pas de token. Ils fonctionnent quand même (le header Authorization est ignoré côté serveur). Exemples :

```ts
// Ranking public
api.get<RankingEntry[]>('/ranking?limit=100');

// Alliances top public
api.get<AllianceSummary[]>('/alliances');

// Détail alliance public
api.get<AllianceDetail>('/alliances/' + id);

// Catalogue events expéditions
api.get<{ id, title, weight }[]>('/expeditions/events');
```

## Wrappers à ajouter en Phase 2

Wrappers manquants à créer (cf. `docs/06_dev_frontend.md` section 13) :

```ts
// api/tech.ts
export const techApi = {
  tree: () => api.get<TechTree>('/tech/tree'),
  research: (tech_id: string) => api.post<...>('/tech/research', { tech_id }),
  complete: () => api.post<...>('/tech/research/complete'),
};

// api/daily.ts
export const dailyApi = {
  status: () => api.get<DailyStatus>('/daily/status'),
  login: () => api.post<DailyLoginResponse>('/daily/login'),
  claimMission: (id: string) => api.post<...>(`/daily/missions/${id}/claim`),
};

// api/scars.ts (existe partiellement dans shipsApi.scars)
// api/missions.ts à créer
// api/galaxy.ts à créer
// api/fleets.ts à créer
// api/combat.ts à créer
// api/expeditions.ts à créer
// api/alliances.ts à créer
```
