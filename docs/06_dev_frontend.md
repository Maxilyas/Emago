# Agent 6 — Dev Frontend

> Détail des 14 pages, 14+ composants, hooks, stores Zustand, client API et infrastructure du frontend React/TypeScript.

---

## 1. Stack et structure

```
frontend/
├── index.html
├── package.json (React 18.3, TS 5.5, Vite 5.3, Tailwind 3.4, Zustand 4.5, TanStack 5.51)
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── UIUX_SPEC.md
└── src/
    ├── main.tsx                 # bootstrap, QueryClient, Toaster
    ├── App.tsx                  # routes + auth guards
    ├── index.css                # design system Tailwind
    ├── api/
    │   ├── index.ts             # forgeApi, planetsApi, rankingApi, authApi
    │   └── ships.ts             # shipsApi (+ modules + scars)
    ├── lib/
    │   ├── api.ts               # ApiError, request<T>, refresh silent 401
    │   └── utils.ts             # cn, fmt, fmtCountdown, rarityColor, xpProgress
    ├── stores/
    │   ├── authStore.ts         # tokens, playerId, persist
    │   └── gameStore.ts         # WS events, notifications, overlays
    ├── hooks/
    │   ├── useGameSocket.ts     # WebSocket auto-reconnect + ping
    │   └── useCountdown.ts
    ├── types/
    │   └── index.ts             # tous les types + UI configs
    ├── pages/                   # 14 pages
    └── components/              # ships, planets, galaxy, combat, buildings, daily, layout, forge, ui
```

---

## 2. Bootstrap (`main.tsx`)

```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) =>
        error.message.includes('4') ? 0 : failureCount < 2,
    },
  },
});

<React.StrictMode>
  <QueryClientProvider client={queryClient}>
    <App />
    <Toaster position="top-right" toastOptions={{
      style: { background: '#1c2333', color: '#fff', border: '1px solid #2d3a50' },
    }}/>
    <ReactQueryDevtools initialIsOpen={false}/>
  </QueryClientProvider>
</React.StrictMode>
```

## 3. Routing (`App.tsx`)

```
/login                    → LoginPage           (RedirectIfAuth)
/                         → Navigate → /dashboard
[RequireAuth + AppLayout] :
  /dashboard              → DashboardPage
  /planets/:id            → PlanetPage
  /buildings              → BuildingsPage
  /hangar                 → HangarPage
  /hangar/:id             → ShipDetailPage
  /forge                  → ForgePage
  /galaxy                 → GalaxyPage
  /ranking                → RankingPage
  /expeditions            → ExpeditionPage
  /tech                   → TechPage
  /combat                 → CombatsPage
  /combat/:id             → CombatReportPage     (ordre liste avant détail)
  /alliances              → AlliancesPage
*                         → Navigate → /
```

Auth guards :
- `<RequireAuth>` : redirige `/login` si pas de `accessToken`, conserve `from` location.
- `<RedirectIfAuth>` : redirige `/dashboard` si déjà connecté.

---

## 4. Stores Zustand

### `authStore.ts`

```ts
interface AuthState {
  accessToken: string | null;       // volatile (mémoire)
  refreshToken: string | null;      // persisté
  playerId: string | null;          // persisté
  username: string | null;          // persisté
  setTokens(access, refresh): void;
  setPlayerId(id, username?): void;
  logout(): void;
  isAuthenticated(): boolean;
  initialize(): Promise<void>;      // auto-refresh au démarrage
}
```

`persist` avec name `'emago-auth'`, `partialize` ne stocke que `refreshToken/playerId/username` (l'access token reste volatil).

`initialize()` est appelé une seule fois dans `App.tsx` via `useEffect([], [])`. Elle POST `/api/v1/auth/refresh` avec le refresh token persisté pour réhydrater l'access token après un rechargement de page. Si le refresh échoue (token expiré ou révoqué) → `logout()` automatique.

### `gameStore.ts` (v1.1)

```ts
interface GameState {
  wsConnected: boolean;
  activeResources: { metal, crystal, deuterium, planetId, updatedAt };
  pendingCombatResult: PendingCombatResult | null;
  spectreData: SpectreAwakeningData | null;       // overlay Grade 5
  pendingForgeResult: PendingForgeResult | null;  // toast enrichi
  notifications: Notification[];                   // max 50, prepend
  // actions...
}
```

Architecture : les overlays globaux (`CombatReport`, `SpectreAwakening`) sont montés dans `AppLayout`. Le store sert de canal de communication entre `useWsEventHandlers` (NotificationPanel) et l'AppLayout.

---

## 5. API client (`lib/api.ts`)

### Caractéristiques

- `BASE_URL = '/api/v1'` (proxy Vite dev → `localhost:8000`, Nginx prod).
- `ApiError` : Error custom avec `status: number, detail: string`.
- **Silent refresh sur 401** : si le token est expiré, intercepteur appelle `POST /auth/refresh` avec le refresh_token, met à jour le store, rejoue la requête. Si échec → `logout()` + throw 401 "Session expirée".
- Helpers : `api.get<T>`, `api.post<T>`, `api.put<T>`, `api.delete<T>`.
- 204 No Content → return `undefined as T`.

### Wrappers API

```ts
// api/index.ts
forgeApi.start(a, b) / status(id) / history()
planetsApi.list() / get(id)
rankingApi.list(limit) / me()
authApi.register/login

// api/ships.ts
shipsApi.list / get / build / demolish / scars / missions
shipsApi.modules.list / install / remove
```

---

## 6. Hook WebSocket (`useGameSocket.ts` v2.1)

Caractéristiques v2.1 :
- URL construite depuis `window.location` (sans variable d'env). Dev : Vite proxy `/ws`. Prod : Nginx proxy `/ws`. Auto `wss:` si HTTPS.
- Reconnexion : backoff exponentiel jusqu'à 30 s max.
- Keepalive : ping toutes les 30 s.
- Handlers délégués au custom hook `useWsEventHandlers` (depuis `NotificationPanel`).

Events serveur dispatchés :
- `combat.result` → `handleCombatResult` (ouvre overlay CombatReport).
- `forge.complete` → `handleForgeComplete` (toast enrichi + invalidate).
- `ship.grade_up` → `handleGradeUp` (si new_grade=5 → SpectreAwakening).
- `ship.scar_earned` → `handleScarEarned` (toast cicatrice).
- `fleet.arrived` → `handleFleetArrived` (invalidate fleets).
- `connected`, `pong` → noop.

Méthode exposée : `pollForge(forgeId)` — fallback REST→WS si forge en cours pendant déconnexion.

---

## 7. Pages — détail (14 pages)

### `LoginPage.tsx` (`/login`)

Dual-tab login/register. Fond étoilé décoratif (80 stars statiques + 3 nébuleuses radial-gradient). API : `authApi.login`/`register` → `setTokens` → navigate `/dashboard`. Animation fade-in + translate-y au mount.

### `DashboardPage.tsx` (`/dashboard`)

Quartier général. Queries (refetch 30 s sauf indiqué) :
- `planetsApi.list`, `forgeApi.history`, `/fleets` (10 s), `/ships`, `/ranking/me`, `forgeApi.status(id)` × N.

Sections : header username + rang, DailyPanel compact, carte planète natale, 4 stats empire, flottes en transit (limit 4) avec FleetCountdown, forges en cours (ForgeProgress), activité récente (5 notifications).

### `PlanetPage.tsx` (`/planets/:id`)

Détail planète. Query `/planets/:id` (30 s).
Sous-composants inline : `ResourceCounter` (interpolation 1s base + rate × elapsed h, cap capacity), `BuildQueueBar` (countdown), `BuildingCard`. Mutation `POST /planets/:id/build` invalide `['planet', id]`.

### `BuildingsPage.tsx` (`/buildings`)

Vue infrastructure complète. Sélecteur planète, sections : EN CONSTRUCTION, ⚡ ÉNERGIE (`EnergyGauge` avec consommation par mine), ⛏️ PRODUCTION (3 mines), 🏭 CHANTIER NAVAL (`ShipyardZone` avec `SHIP_TYPES_BY_LEVEL`), 🔬 RECHERCHE, 🌌 EXPÉDITIONS. Mutation enrichie avec toast `next_unlock`.

### `HangarPage.tsx` (`/hangar`)

Liste vaisseaux + filtres + modal build avec révélation. Filtres status (DOCKED/IN_FLEET/IN_FORGE/all) + rareté (5 boutons round). `BuildModal` plein écran (sélecteur ship_type, planet, note RNG 55/27/12/5/1%). `RarityReveal` animé sur build success.

### `ShipDetailPage.tsx` (`/hangar/:id`)

Tabs Stats / Modules / Cicatrices. `ShipStatPanel` affiche stats serveur (jamais calculé client). `ModuleManager` : grid slots avec premium (bordure jaune dashed). `InstallModuleModal` : 6 module types × 5 niveaux (4-5 désactivés sur slot standard). Démolition avec confirm() si DOCKED. Badge Pedigree si `parent_ship_id`.

### `ForgePage.tsx` (`/forge`)

Tabs Forge / Historique. Forge : 2 panels A/B sélection, vaisseaux éligibles `DOCKED && rarity !== 'LEGENDARY'`, filtre compatibilité `same type && same rarity`. Aperçu animé : badge rareté ×2 → flèche → badge rareté suivante (animate-pulse + glow). Bullet "✓ meilleures stats / 30% XP / 8h" + coût `FORGE_COSTS`. Mutation `forgeApi.start` avec spinner.

### `GalaxyPage.tsx` (`/galaxy`)

`GalaxyMap` SVG interactif (orbites concentriques, 15 slots). Sélecteur galaxie 1-9 / système 1-499. `SendFleetModal` (mission ATTACK/TRANSPORT/ESPIONAGE, sélection ships DOCKED, cargo si TRANSPORT). Liste flottes transit (rappel inline) + flottes ennemies (rouge). Refetch 10 s.

### `TechPage.tsx` (`/tech`)

Arbre tech 4 classes. Bandeau recherche active avec `ResearchCountdown`. Sélecteur classes (2×4 grid). `TechCard` : niveaux, bonus_summary, prérequis (désaturation si non remplis), bouton "RECHERCHER → Niv.X+1".

### `ExpeditionPage.tsx` (`/expeditions`)

Lancement (durée SHORT/MEDIUM/LONG, max 5 ships). `EVENT_ICONS` mapping 12 events. `ExpeditionReport` riche : narrative italic, ressources/XP/modules/scars/deut perdu. Refetch 10 s pour détecter complétion.

### `RankingPage.tsx` (`/ranking`)

Top 100 + position perso. Refetch 60 s. Highlighting de la ligne joueur.

### `AlliancesPage.tsx` (`/alliances`)

Liste top 50 + détail (membres, guerres). Boutons création/join/quit/déclarer guerre. Validation côté UI : tag uppercase 2-5 chars regex.

### `CombatsPage.tsx` (`/combat`)

Historique combats (limit 50). Lignes cliquables → `/combat/:id`.

### `CombatReportPage.tsx` (`/combat/:id`)

Rapport détaillé d'un combat. Réutilise le composant `CombatReport` de la layer combat.

---

## 8. Composants

### `ships/`

- **`ShipCard.tsx`** : carte vaisseau pour grilles. Modes `compact`, `selected`. Couleur rareté + glow. Affiche classe, status, grade. Hover lift -2px.
- **`ShipStatPanel.tsx`** : stats compared base vs current. Indicator `cap_reached`.
- **`RarityReveal.tsx`** : overlay animé révélant la rareté d'un nouveau ship (RARE+).
- **`SpectreAwakening.tsx`** : overlay full-screen autonome, déclenché par `gameStore.spectreData` quand `grade_up.new_grade = 5`. Indépendant des types globaux.

### `planets/`

- **`ResourceBar.tsx`** : métal/cristal/deutérium avec interpolation côté client.

### `galaxy/`

- **`GalaxyMap.tsx`** : SVG interactif 15 slots orbitaux. Halos hover/sélection. `onSelectPlanet(slot)` callback (uniquement si planet_id).

### `combat/`

- **`CombatReport.tsx`** : rapport complet d'un combat (rounds animés, XP, pertes, cicatrices, synergies). Utilisé en page (`/combat/:id`) et en overlay (depuis `pendingCombatResult` du store).

### `buildings/`

- **`BuildingCardUX.tsx`** : carte enrichie (catégorie couleur, production marginale via `ProductionDelta`, accordion détails synergies/déverrouillages/tip).
- **`BuildingTooltip.tsx`** : tooltip riche au survol.

### `daily/`

- **`DailyPanel.tsx`** : streak 7 jours + 3 missions. Mode `compact` (Dashboard) ou full.

### `forge/`

- **`ForgeProgress.tsx`** : barre + countdown via `useCountdown(eta_seconds)`. Badge `is_drift` si dérivée.

### `layout/`

- **`AppLayout.tsx`** : navigation principale (sidebar, header). Active `useGameSocket()`. Monte 2 overlays globaux : `<CombatReport>` et `<SpectreAwakening>`.
- **`NotificationPanel.tsx`** : panneau notifications WS, dot rouge sur cloche pour unread. Exporte `useWsEventHandlers()` consommé par `useGameSocket`.

### `ui/`

- **`index.tsx`** exporte : `Badge`, `Modal`, `Tabs`, `Skeleton`, `EmptyState`, `LoadingSpinner`.

---

## 9. Helpers (`lib/utils.ts`)

```ts
cn(...inputs)              // twMerge(clsx(...))
fmt(n, decimals=0)         // toLocaleString('fr-FR', { maxFractionDigits })
fmtShort(n)                // 1.5M / 1.2k / 123
fmtCountdown(seconds)      // HH:MM:SS, '00:00:00' si ≤0
rarityColor(r)             // RARITY_CONFIG[r].color
rarityTw(r)                // RARITY_CONFIG[r].tw classes Tailwind
rarityGlow(r)              // box-shadow string (LEGENDARY double)
timeAgo(dateStr)           // date-fns formatDistanceToNow fr
fmtDate(dateStr)           // dd/MM/yyyy HH:mm fr
xpProgress(currentXp, currentGrade)  // 0-100, hard-coded thresholds
clamp(val, min, max)
```

---

## 10. Hook `useCountdown.ts`

```ts
useCountdown(etaSeconds, onComplete?)
  → { remaining: number, pct: number, done: boolean }
```

Interpolation 1 s côté client. Refs `startedAt`, `initialEta`, `completedRef`. `onComplete` appelé une seule fois quand `remaining <= 0`. Si `etaSeconds` change → reset.

---

## 11. Configuration constants (`types/index.ts`)

### `RARITY_CONFIG`, `GRADE_CONFIG`, `SHIP_TYPE_CONFIG`, `MODULE_CONFIG`, `FORGE_COSTS`

Cf. doc UI/UX (Agent 4) section 11.

---

## 12. Patterns récurrents

- **Cache invalidation** : après mutation, `queryClient.invalidateQueries(['key'])` puis refetch automatique. Souvent invalidate après WS events.
- **Refetch intervals** : Dashboard 30 s, fleets 10 s, expeditions 10 s, ranking 60 s, planets 15-30 s.
- **Countdowns** : interpolation locale via `useCountdown` ou `useEffect+setInterval`. Source de vérité = serveur (refetch).
- **Helpers `hexToRgb`** : dupliqués dans plusieurs composants (`BuildingsPage`, `TechPage`). Candidat pour extraction utilitaire.
- **Animations Tailwind** : `animate-fade-in` (page-level), `animate-slide-up` (modals), `animate-pulse` (badges actifs), `animate-spin` (spinners).
- **Couleurs sémantiques** : `text-red-400` (erreurs), `text-green-400` (succès), `text-blue-400` (actions), `text-yellow-400` (LEGENDARY/avertissements).

---

## 13. Améliorations Frontend à prévoir

| Tâche | Priorité |
|---|---|
| Page Profil joueur | Moyenne |
| Tests Vitest + React Testing Library (Hangar, Forge, ShipDetail, Combat) | Haute |
| Extraction helper commun `hexToRgb` dans `lib/utils.ts` | Basse |
| Optim re-renders `ResourceBar` (memo, useCallback) | Moyenne |
| Affichage cicatrices sur ShipCard (tooltip narratif) | Moyenne |
| Affichage Pedigree dans ShipDetail (mention parent + lignée) | Moyenne |
| API tech.ts (wrapper) | Moyenne |
| API daily.ts (wrapper) | Moyenne |
| API scars/missions wrappers | Moyenne |
| Flow onboarding / tutoriel | Haute |
| Animations skins / cosmétiques | Basse |
| Heartbeat handling (timeout reconnect plus agressif) | Moyenne |
| Page espionnage (Phase 2) | Phase 2 |
| Page marché galactique (Phase 2) | Phase 2 |
| Page profil détaillé alliance | Phase 2 |

---

*Document Agent 6 — Mai 2026*
