# Spec écran : {Nom}

| Champ | Valeur |
|---|---|
| **Route** | `/...` |
| **Composant page** | `XxxPage.tsx` |
| **Auth requise** | Oui (RequireAuth) / Non |
| **Audience** | Tous / Leader d'alliance / … |
| **Densité** | Compact / Immersif |
| **Date spec** | YYYY-MM-DD |
| **Auteur** | Agent 4 |

---

## 1. Objectif

{1-2 paragraphes : que vient faire le joueur sur cet écran, quel est le résultat attendu, comment ça s'inscrit dans la boucle de gameplay.}

---

## 2. Layout général

{ASCII mockup ou description textuelle du layout.}

```
┌────────────────────────────────────────────────────────┐
│  Header (titre + actions principales)                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Section 1 (panel principal)                          │
│  ┌──────────────┬──────────────┬──────────────┐        │
│  │  Card        │  Card        │  Card        │        │
│  └──────────────┴──────────────┴──────────────┘        │
│                                                        │
│  Section 2 (sidebar ou autre panel)                    │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Hiérarchie visuelle** :
1. {Élément le plus important — pourquoi}
2. {Second — pourquoi}
3. {Tertiaire — pourquoi}

---

## 3. Composants

### Composants réutilisés (existants)

| Composant | Usage |
|---|---|
| `<ShipCard>` | … |
| `<ResourceBar>` | … |
| `<LoadingSpinner>` | État chargement |
| `<EmptyState>` | État vide |
| `<Modal>` | … |
| `<Badge>` | … |

### Nouveaux composants à créer

| Nom | Rôle | Props clés |
|---|---|---|
| `<XxxCard>` | … | `data: XxxData, onSelect?` |

---

## 4. États

### Normal (avec données)
{Description}

### Chargement initial
{Skeleton ? Spinner ? Quel layout ?}

### Vide
{Texte + icône + CTA}

### Erreur
{Toast + message ? Bandeau d'erreur ?}

### Succès (mutation)
{Toast vert + invalidation queries}

---

## 5. Données

### Endpoints API

| Méthode | URL | Quand | Refetch | Query key |
|---|---|---|---|---|
| GET | `/...` | Au mount | 30 s | `['xxx']` |
| POST | `/...` | Sur action user | — | (mutation, invalidate `['xxx']`) |

### Events WebSocket écoutés

| Event | Effet UI |
|---|---|
| `xxx.event` | Toast + invalidate `['xxx']` |

---

## 6. Interactions

| Action utilisateur | Effet UI | Endpoint | Validation client |
|---|---|---|---|
| Click "..." | Modal s'ouvre | — | — |
| Submit modal | Spinner button + POST | `POST /...` | {liste validations} |
| Hover ShipCard | Glow renforcé | — | — |
| Click row | Navigate | `/.../:id` | — |

---

## 7. Animations

| Animation | Trigger | Durée | Classe Tailwind |
|---|---|---|---|
| Fade-in page | Mount | 0.3s | `animate-fade-in` |
| Slide-up modal | Modal opens | 0.25s | `animate-slide-up` |
| Pulse badge nouveau | Si data fresh | 2.5s loop | `animate-pulse` |

---

## 8. Accessibilité

- ☐ Focus visible (outline ring blue accent).
- ☐ Tab order logique (haut → bas, gauche → droite).
- ☐ Contraste texte ≥ 4.5:1 (WCAG AA).
- ☐ aria-label sur boutons icon-only.
- ☐ aria-live pour notifications dynamiques (toast).
- ☐ Échap ferme les modals.
- ☐ Boutons primaires accessibles à la souris ET clavier.

---

## 9. Mobile-first (375px+)

| Breakpoint | Adaptation |
|---|---|
| 375px (default) | Stack vertical, sidebar masquée, header sticky |
| 640px (`sm:`) | … |
| 768px (`md:`) | Layout 2 colonnes |
| 1024px (`lg:`) | … |

Notes spécifiques :
- {ex. les modals deviennent plein écran < 640px}
- {ex. les listes dépassent 5 items → scroll vertical interne}

---

## 10. Notes pour Agent 6 (impl frontend)

### Hooks à utiliser
- `useGameSocket` (déjà actif au niveau AppLayout, pas à ré-instancier).
- `useAuthStore()` pour playerId/username.
- `useGameStore()` pour `activeResources` si applicable.
- `useCountdown(eta_seconds, onComplete)` si countdown.

### Patterns à respecter
- Pas de calcul `current_stats` côté client — toujours utiliser ce que retourne `/ships/{id}`.
- Rareté lue depuis `RARITY_CONFIG[rarity]` ou helpers `rarityColor / rarityTw / rarityGlow`.
- Toast erreur sur `ApiError` : `toast.error(err.detail ?? 'Erreur')`.
- Invalidation query après mutation, pas de set state manuel.

### Query keys recommandées
- `['xxx']` pour la liste.
- `['xxx', id]` pour le détail.
- `['xxx-active', playerId]` pour les actifs.

---

## 11. Liens et références

- Doc Agent 4 : [`docs/04_uiux_designer.md`](../04_uiux_designer.md).
- Doc Agent 6 : [`docs/06_dev_frontend.md`](../06_dev_frontend.md).
- API référence : [`docs/03_architecte.md`](../03_architecte.md) section 3.
- Types TS : `frontend/src/types/index.ts`.
- Endpoints concernés : {liste si applicable}.
