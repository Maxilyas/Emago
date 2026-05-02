---
name: emago-page-scaffold
description: Génère une nouvelle page React/TypeScript Emago en respectant les patterns du projet — TanStack Query (refetch interval adapté), Zustand (useAuthStore + useGameStore), useGameSocket events, classes Tailwind du design system Emago (.panel/.btn-primary/.input-field/glow rareté), animations animate-fade-in/slide-up, mobile-first 375px+, layout via AppLayout, gestion erreurs ApiError + react-hot-toast. Sortie un fichier frontend/src/pages/<Name>Page.tsx prêt à connecter aux endpoints API. Use when l'utilisateur dit "scaffold page Emago", "nouvelle page React", "page espionnage", "page profil joueur", "page marché galactique", "ajoute /alliance/profile".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 6-dev-frontend
---

# emago-page-scaffold

Génère des pages React/TypeScript Emago cohérentes avec l'architecture frontend existante. Encapsule tous les patterns connus pour démarrer immédiatement.

---

## Quand utiliser ce skill

- Implémenter un écran spécifié par Agent 4 (`emago-screen-spec`).
- Créer une page Phase 2 (espionnage, marché galactique, profil joueur).
- Refondre une page existante en suivant les conventions actuelles.

## Quand NE PAS utiliser ce skill

- Pour un composant isolé (pas une page entière) → utilise `emago-component-react-emago`.
- Pour un handler WebSocket → utilise `emago-ws-handler-emago`.
- Pour la spec UI/UX (avant impl) → utilise `emago-screen-spec`.

---

## Instructions

### Étape 1 — Cadrer la page

Demande à l'utilisateur (ou récupère depuis une spec `emago-screen-spec` existante) :

1. **Nom de la page** + route React Router (ex. `EspionagePage` → `/espionage`).
2. **Endpoints API** utilisés (GET / POST / PUT / DELETE) + URL.
3. **Refetch intervals** souhaités (Dashboard 30s, fleets 10s, ranking 60s — par défaut 30s).
4. **Events WebSocket** écoutés (`espionage.report_ready`, etc.).
5. **State global** : a-t-on besoin de `useGameStore.activeResources` ? Du `username` de `useAuthStore` ?
6. **Sous-composants** internes inline ou composants réutilisables existants à importer.
7. **Modal / overlay** nécessaire ?

### Étape 2 — Vérifier les conventions Emago

Cf. `references/page_template.tsx` qui encapsule :

**Imports standards** :
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useGameStore } from '@/stores/gameStore';
import { api, ApiError } from '@/lib/api';
import { LoadingSpinner, EmptyState, Modal } from '@/components/ui';
import toast from 'react-hot-toast';
import { useState, useEffect } from 'react';
```

**Pattern de base** :
- TanStack Query pour fetch (jamais `useEffect + fetch` direct).
- Mutation avec `onSuccess` invalidant les queries concernées + toast.
- `if (isLoading)` → `<LoadingSpinner />` ou skeletons.
- `if (!data?.length)` → `<EmptyState />` avec CTA.
- Conteneur principal `<div className="animate-fade-in space-y-4">`.

**Routing** :
- Exporter par défaut : `export default function NomPage() { ... }`.
- Ajouter dans `frontend/src/App.tsx` la route correspondante (sous `<RequireAuth>` + `<AppLayout>`).
- Ordre routes : statiques avant paramétrées (cf. `/forge/history` avant `/forge/{id}`).

**Stores** :
- `useAuthStore()` : pour `playerId, username, accessToken`.
- `useGameStore()` : pour `activeResources, notifications, pendingForgeResult`.
- Ne pas créer de nouveau store pour une page locale — utiliser `useState` local.

**Erreurs** :
- `try/catch` minimal — TanStack Query gère.
- `onError: (err: any) => toast.error(err.detail ?? 'Erreur serveur')`.
- 401 silent refresh est déjà géré par `lib/api.ts`.

### Étape 3 — Générer le code

Utilise `references/page_template.tsx` comme base. Adapte :
- Nom du composant (PascalCase, suffixe `Page`).
- Endpoints API (URL + types TS).
- Refetch interval (`refetchInterval: 30_000` par défaut, 10s pour fleets/expeditions, 60s pour ranking).
- Sous-sections (chaque carte / section dans son `<section className="panel p-4">`).

### Étape 4 — Créer/réutiliser les types

Vérifie `frontend/src/types/index.ts` :
- Si la page utilise des types existants (ShipSummary, PlanetDetail, etc.) → import.
- Si nouveaux types → ajouter dans `types/index.ts` (jamais inline dans la page).

### Étape 5 — Wrapper API si manquant

Vérifie `frontend/src/api/index.ts` et `frontend/src/api/ships.ts` :
- Si la route est nouvelle → ajouter un wrapper `xxxApi.list/get/create/update/delete`.
- Préférer ces wrappers à des `api.get('...')` inline pour la maintenabilité.

### Étape 6 — Ajouter la route dans `App.tsx`

```tsx
<Route element={<RequireAuth><AppLayout /></RequireAuth>}>
  ...
  <Route path="/<nom>" element={<NomPage />} />
  // si paramétrée : la mettre APRÈS la liste
  <Route path="/<nom>/:id" element={<NomDetailPage />} />
</Route>
```

### Étape 7 — Mise à jour `docs/06_dev_frontend.md`

Ajouter la nouvelle page à la table section 7 (catalogue des 14 pages) → 15+.

### Étape 8 — Suggestions Agent 4 / Agent 6

Si la page introduit un nouveau composant réutilisable (`<XxxCard>`, `<XxxPanel>`) :
- Suggérer d'extraire dans `frontend/src/components/<feature>/` au lieu de l'inliner.
- Documenter dans `docs/04_uiux_designer.md` section 8 (catalogue composants).

---

## Examples

### Exemple 1 — Page espionnage

**User** : "Scaffold la page d'espionnage. Endpoints : GET /espionage/probes (refetch 30s), POST /espionage/probe, GET /espionage/reports (refetch 30s). WS event : espionage.report_ready"

**Actions** :
1. Génère `EspionagePage.tsx` avec 2 queries (probes, reports) + 1 mutation (lancer sonde).
2. Layout : header + 3 panneaux (lancer sonde / probes en cours / rapports reçus).
3. Sous-composant inline `<ProbeCard>` avec countdown.
4. Modal sélection cible + ships (réutilise `<ShipCard compact>`).
5. Handler WS `espionage.report_ready` → invalidate `['espionage-reports']` + toast.
6. Ajoute route `/espionage` dans App.tsx.
7. Suggère : ajouter `espionageApi` dans `api/index.ts` ; ajouter types `Probe, EspionageReport` dans `types/index.ts`.

### Exemple 2 — Page profil joueur

**User** : "Crée la page Profil avec stats + historique combats + alliance + vaisseaux Légendaires"

**Actions** :
1. Layout : hero + tabs Stats / Combats / Vaisseaux glorieux / Alliance.
2. Reuse `<Tabs>` + `<ShipCard>` + `<CombatReport>` (mini).
3. Queries : `/players/me/profile` (stats), `/combat/history?limit=20`, `/ships?rarity=LEGENDARY` (filter via TanStack `select`).
4. State local `tab` (défaut Stats).
5. Mobile : tabs scrollable horizontalement, sections empilées.

### Exemple 3 — Refonte page existante

**User** : "Refonds la page Hangar avec un nouveau layout grid + filtres avancés"

**Actions** :
1. Charge `frontend/src/pages/HangarPage.tsx`.
2. Identifie les conventions actuelles (BuildModal, RarityReveal, filtres rareté+status).
3. Propose nouveau layout en respectant les patterns existants.
4. Garde la logique TanStack Query identique (juste UI change).

---

## Troubleshooting

### Type API inconnu

**Cause** : nouveau endpoint sans type TS défini.
**Solution** : ajouter dans `types/index.ts` (jamais inline). Demander à Agent 5 le shape exact si pas évident.

### Queries qui dupliquent

**Cause** : 2 pages utilisent `useQuery({queryKey: ['ships']})` mais avec des paramètres différents.
**Solution** : inclure les params dans la queryKey : `['ships', { status: 'DOCKED' }]`.

### Re-renders excessifs sur countdowns

**Cause** : countdown qui tick chaque seconde re-render toute la page.
**Solution** : extraire le countdown dans un sous-composant isolé (cf. `FleetCountdown` inline dans `DashboardPage`).

### WebSocket event reçu mais UI pas mise à jour

**Cause** : oubli de `qc.invalidateQueries(...)` dans le handler `useWsEventHandlers`.
**Solution** : toujours invalider la query concernée. Si data immutable in-place pendant l'event (ex. update Zustand store), c'est ok aussi.

### Mobile-first cassé

**Cause** : usage de `flex flex-row` sans breakpoint, ou grille fixe.
**Solution** : `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` ; `flex flex-col md:flex-row` ; tester à 375px.

### Toast d'erreur affiche `[object Object]`

**Cause** : `toast.error(err)` au lieu de `toast.error(err.detail)`.
**Solution** : toujours `toast.error(err.detail ?? 'Erreur serveur')`. `ApiError.detail` est garanti string.

---

## References

- `references/page_template.tsx` — template TSX complet prêt à copier.
- `references/page_patterns.md` — patterns récurrents (refetch interval, countdown inline, modal, etc.).
- `references/api_client_usage.md` — comment utiliser `lib/api.ts` (silent refresh, ApiError).
- `references/types_existing.md` — résumé des types globaux disponibles.
