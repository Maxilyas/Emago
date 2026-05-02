---
name: emago-component-scaffold
description: Génère un composant React/TypeScript réutilisable Emago (carte vaisseau, panel ressources, badge rareté, modal, countdown…) ou un handler d'event WebSocket dans useWsEventHandlers, en respectant le design system — palette rareté canonique, classes Tailwind .panel/.btn-primary/.glow-{rarity}, props typées strict, mobile-first 375px+, pas de any TypeScript. Met à jour docs/06_dev_frontend.md. Use when l'utilisateur dit "composant React Emago", "crée un composant", "nouveau composant", "handler WS event", "ajoute event WebSocket frontend", "composant espionnage", "badge alliance".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 6-dev-frontend
---

# emago-component-scaffold

Génère des composants React/TypeScript cohérents avec le design system Emago. Couvre aussi les handlers d'événements WebSocket dans `useWsEventHandlers`.

---

## Quand utiliser ce skill

- Créer un composant réutilisable extrait d'une page (ShipCard, ResourceBar, ProbeReportCard…).
- Ajouter un handler d'event WebSocket dans `NotificationPanel.tsx` → `useWsEventHandlers`.
- Refondre un composant existant pour l'aligner sur le design system actuel.

## Quand NE PAS utiliser ce skill

- Pour une page entière → utilise `emago-page-scaffold`.
- Pour la spec UX du composant (avant impl) → utilise `emago-component-spec` (Agent 4).
- Pour un store Zustand → gérer dans `emago-page-scaffold` ou directement.

---

## Instructions

### Étape 1 — Cadrer le composant

Demande :
1. **Nom** (PascalCase, ex. `ProbeReportCard`).
2. **Localisation** : `frontend/src/components/<feature>/` ou `components/ui/` si générique.
3. **Props** : liste des entrées du composant (avec types TypeScript).
4. **Interactions** : clics, hovers, actions (callback `onAction`).
5. **États** : normal / loading / erreur / vide / actif.
6. **Event WS** (si handler) : nom de l'event (`espionage.report_ready`), payload shape.

### Étape 2 — Vérifier le design system

Appliquer obligatoirement (cf. `references/design_system_components.md`) :

**Palette rareté** (jamais d'autre couleur pour communiquer la rareté) :
```ts
const RARITY_COLORS: Record<string, string> = {
  COMMON:    'text-gray-400 border-gray-500',
  UNCOMMON:  'text-green-400 border-green-500',
  RARE:      'text-blue-400 border-blue-500',
  EPIC:      'text-purple-400 border-purple-500',
  LEGENDARY: 'text-yellow-400 border-yellow-500',
}
```

**Classes Tailwind standard** :
- Conteneurs : `.panel` (`bg-panel border border-border rounded-lg`), `.panel-glass`, `.panel-glow`.
- Boutons : `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost`.
- Inputs : `.input-field`.
- Glow rareté : `.glow-common`, `.glow-uncommon`, `.glow-rare`, `.glow-epic`, `.glow-legendary`.
- Animations : `animate-fade-in` (apparition), `animate-slide-up` (modals), `animate-pulse` (badges actifs).

**Mobile-first** : tous les composants doivent fonctionner à 375px de largeur.

### Étape 3 — Générer le composant

Template de base :

```tsx
import React from 'react'

interface <Name>Props {
  // props typées strictement — pas de any
  field: Type
  onAction?: (value: Type) => void
}

export function <Name>({ field, onAction }: <Name>Props) {
  return (
    <div className="panel p-4 animate-fade-in">
      {/* Contenu */}
    </div>
  )
}
```

Règles :
- Props interface dans le même fichier (sauf si partagée → `types/index.ts`).
- Export nommé (pas default pour les composants).
- Jamais de `any` TypeScript.
- `onAction?: (value: Type) => void` pour les callbacks optionnels.
- Utiliser `useAuthStore` / `useGameStore` depuis les stores Zustand si besoin de state global.

### Étape 4 — Handler WebSocket (si applicable)

Les events WS sont gérés dans `frontend/src/components/layout/NotificationPanel.tsx` → `useWsEventHandlers`.

Pour ajouter un handler :

```tsx
// Dans useWsEventHandlers() :
const handleEspionageReport = useCallback((data: EspionageReportData) => {
  // 1. Mettre à jour le store si nécessaire
  // 2. Invalider les queries TanStack Query
  qc.invalidateQueries({ queryKey: ['espionage-reports'] })
  // 3. Toast de notification
  toast.success(`Rapport d'espionnage reçu : ${data.target_username}`)
}, [qc])

// Retourner dans l'objet handlers :
return {
  ...existingHandlers,
  handleEspionageReport,
}
```

Et ajouter dans `useGameSocket.ts` switch case :
```ts
case 'espionage.report_ready': handlers.handleEspionageReport(event.data); break
```

### Étape 5 — Typer les données

Vérifier `frontend/src/types/index.ts` :
- Si le type existe → importer.
- Si nouveau → ajouter dans `types/index.ts` (jamais inline dans le composant).

```ts
// types/index.ts
export interface EspionageReportData {
  report_id: string
  target_username: string
  resources_visible: boolean
  fleets_visible: boolean
  detected: boolean
}
```

### Étape 6 — Enregistrer le composant

Si composant réutilisable (pas inline dans une page) :
- Ajouter l'export dans `frontend/src/components/<feature>/index.ts` (barrel export).
- Ou créer le barrel si inexistant.

### Étape 7 — Mettre à jour `docs/06_dev_frontend.md` (obligatoire)

- Section sur les composants : ajouter le nouveau composant avec ses props et son rôle.
- Si nouveau handler WS : ajouter dans la section hooks/useGameSocket.

---

## Examples

### Exemple 1 — Composant ProbeReportCard

**User** : "Crée le composant ProbeReportCard pour afficher un rapport d'espionnage"

**Actions** :
1. Props : `report: EspionageReport` (type à créer dans `types/index.ts`).
2. Layout : panel avec header (cible + date) + body (ressources vues si detected=false, sinon badge "Détecté").
3. Couleur : blue accent si rapport propre, orange si détecté.
4. Mobile : vertical stack, header compact.
5. Export nommé `ProbeReportCard` dans `components/espionage/`.
6. Met à jour docs.

### Exemple 2 — Handler WS espionage.report_ready

**User** : "Ajoute le handler WebSocket pour l'event espionage.report_ready"

**Actions** :
1. Lit `frontend/src/components/layout/NotificationPanel.tsx`.
2. Ajoute `handleEspionageReport` dans `useWsEventHandlers`.
3. Invalide `['espionage-reports']` pour déclencher le refetch.
4. Toast : "Rapport d'espionnage reçu — [target_username]".
5. Ajoute le case dans `useGameSocket.ts`.
6. Ajoute le type `EspionageReportData` dans `types/index.ts`.
7. Met à jour docs.

### Exemple 3 — Refonte d'un composant existant

**User** : "Modernise ShipCard pour afficher les cicatrices si présentes"

**Actions** :
1. Lit `frontend/src/components/ships/ShipCard.tsx`.
2. Ajoute prop `scars?: ShipScar[]` (optionnel, backward compatible).
3. Si `scars?.length > 0` → ajouter section "Cicatrices" avec badges sous la carte.
4. Style badge : `text-xs text-amber-400 border border-amber-600 rounded px-1`.
5. Tests mobiles : à 375px, badges sous les stats sans overflow.

---

## Troubleshooting

### Toast affiche `[object Object]`

**Cause** : `toast.error(err)` au lieu de `toast.error(err.detail ?? 'Erreur')`.
**Solution** : toujours destructurer l'erreur.

### Handler WS déclenche des re-renders en cascade

**Cause** : invalidation de plusieurs queries dans le handler.
**Solution** : utiliser `qc.invalidateQueries` avec des keys précises (pas `qc.invalidateQueries({})` qui invalide tout).

### Le composant ne s'affiche pas correctement à 375px

**Cause** : utilisation de `flex-row` ou `grid-cols-X` sans breakpoint.
**Solution** : `flex flex-col sm:flex-row` ; `grid grid-cols-1 sm:grid-cols-2`.

### Props TypeScript non vérifiées

**Cause** : usage de `any` ou type trop large.
**Solution** : définir un type précis dans `types/index.ts`, importer dans le composant. Ne jamais écrire `props: any`.

---

## References

- `references/design_system_components.md` — palette, classes Tailwind, animations Emago.
- `references/component_patterns.md` — patterns récurrents (ShipCard, ResourceBar, CountdownTimer, Modal).
- `references/ws_event_handlers.md` — handlers WS existants et leur structure.
- `references/types_existing.md` — types TypeScript disponibles dans `types/index.ts`.
