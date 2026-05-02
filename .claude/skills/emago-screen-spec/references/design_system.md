# Design system Emago — référence rapide

Extraits de `docs/04_uiux_designer.md` à utiliser systématiquement pour toute spec d'écran.

## 1. Palette de rareté (canon, jamais s'écarter)

| Rareté | Hex | Tailwind classes | Effet spécial |
|---|---|---|---|
| COMMON | `#9E9E9E` | `text-gray-400 border-gray-500` | — |
| UNCOMMON | `#4CAF50` | `text-green-400 border-green-500` | — |
| RARE | `#2196F3` | `text-blue-400 border-blue-500` | — |
| EPIC | `#9C27B0` | `text-purple-400 border-purple-500` | — |
| LEGENDARY | `#FFD700` | `text-yellow-400 border-yellow-400` | `glow-legendary` (double-layer + animate-pulse-glow) |

**Helpers TS** : `rarityColor(r)`, `rarityTw(r)`, `rarityGlow(r)` depuis `@/lib/utils`.

## 2. Couleurs surfaces

```
--void:           #050810   (fond principal page)
--panel:          rgba(13,18,30,0.85)  (panneaux, backdrop-filter blur 12px)
--border:         rgba(35,50,70,0.8)
--surface-secondary: #0d1220
--surface-tertiary:  #131b2e
--surface-elevated:  #1a2540
```

## 3. Couleurs accent

| Accent | Hex | Usage |
|---|---|---|
| blue | `#2d7dd2` | actions principales, focus |
| violet | `#7c3aed` | éléments narratifs, Dérive |
| cyan | `#06b6d4` | infos, tooltips |
| green | `#10b981` | succès |
| orange | `#f97316` | alertes douces |

## 4. Couleurs ressources

```
metal:      #94a3b8  (gris ardoise)
crystal:    #7dd3fc  (cyan clair)
deuterium:  #86efac  (vert tendre)
energy:     #fbbf24  (doré)
```

## 5. Typographie

| Famille | Usage | Classe |
|---|---|---|
| Orbitron | Display, titres section, badges | `font-display` |
| Inter | Texte courant | `font-sans` (default) |
| JetBrains Mono | Stats numériques | `font-mono` |

## 6. Composants CSS structurels

```
.panel              bg-panel + border + rounded-xl + backdrop-blur 12px
.panel-glass        rgba(17,24,39,0.6) + blur 16px
.panel-glow::before line gradient bleu top
.btn-primary        gradient blue + glow shadow + scale-95 active
.btn-secondary      bg gris foncé hover gradient
.btn-danger         red-400 + bordure red-800
.btn-ghost          texte gray-400 hover white
.input-field        bg dark + bordure + focus ring bleu
.badge              rounded-full uppercase tracking-wider
.section-title      Orbitron uppercase letter-spacing 0.15em
.stat-bar           h-1.5 rounded-full bg-gris-50%
.stat-bar-fill      transition 700ms
.bar-hull           gradient rouge
.bar-shield         gradient bleu
.bar-xp             gradient ambre
.bar-metal          gradient slate
.bar-crystal        gradient sky
.bar-deut           gradient green
```

## 7. Glows par rareté

```
.glow-common    box-shadow 0 0 8px rgba(158,158,158,0.30)
.glow-uncommon  box-shadow 0 0 8px rgba(76,175,80,0.35)
.glow-rare      box-shadow 0 0 8px rgba(33,150,243,0.40)
.glow-epic      box-shadow 0 0 8px rgba(156,39,176,0.45)
.glow-legendary box-shadow 0 0 12px gold66, 0 0 24px gold33 + animate pulse-glow
```

## 8. Animations Tailwind disponibles

| Classe | Durée | Trigger usage |
|---|---|---|
| `animate-fade-in` | 0.3s | page-level |
| `animate-slide-up` | 0.25s | modals |
| `animate-pulse` | 2s loop | badges actifs, recherche en cours |
| `animate-pulse-glow` | 2.5s | LEGENDARY glow |
| `animate-float` | 4s | éléments flottants (vaisseaux) |
| `animate-spin` | — | spinners |
| (`shimmer` custom) | 1.8s | loaders |
| (`forge-burn` custom) | 2s | forge active |
| (`scan` custom) | 4s linear | scan-effect overlay |

## 9. Background décoratif (déjà appliqué globalement)

Sur `body` :
- 3 radial gradients superposés : ellipse bleue 80%/50% à 20%/-10%, ellipse violet 60%/40% à 80%/100%, ellipse cyan 100%/100% à 50%/50%.
- Pseudo `body::before` : 10 étoiles random fixed, pointer-events none.

Donc **ne pas re-déclarer** d'arrière-plan sur les pages — laisser transparent ou semi-transparent.

## 10. Règles UX absolues

1. `current_stats` jamais calculé côté client.
2. Après event WS → invalider queries TanStack.
3. Rareté lue depuis l'API uniquement.
4. Countdowns interpolés client mais source vérité serveur.
5. `cap_reached` : afficher icône 🔒 sur stat plafonnée +150%.
6. Mobile-first 375 px+.
7. Pas de pop-ups intrusifs — sidepanels, overlays doux, modals discrètes.
8. Animations subtiles, pas lourdes (sauf overlays narratifs RarityReveal/SpectreAwakening).
9. Lisibilité prioritaire sur l'esthétique (WCAG AA).

## 11. UI configs (constantes frontend, à utiliser)

```ts
RARITY_CONFIG[rarity]   → { color, label, tw }
GRADE_CONFIG[grade]     → { name, xp }
SHIP_TYPE_CONFIG[type]  → { icon, class }
MODULE_CONFIG[module]   → { stat, icon }
FORGE_COSTS[type]       → { metal, crystal, deuterium }
```

Importables depuis `@/types`.

## 12. Toasts (react-hot-toast)

Position `top-right`. Style :
```
background: '#1c2333'
color: '#fff'
border: '1px solid #2d3a50'
borderRadius: '8px'
```

Themes :
- success : icon `#4CAF50`
- error : icon `#ef4444`
