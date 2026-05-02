# Agent 4 — UI/UX Designer

> Identité visuelle, design system, écrans, composants, animations, palette de rareté, typographie. Spécifications complètes pour Agent 6.

---

## 1. Identité visuelle

### Ambiance

- **Ton** : espace profond, technologie avancée, élégant et lisible.
- **Référence** : Mass Effect (immersif, narratif, sobre) plutôt que Clash of Clans (cartoonish saturé).
- **Anti-référence** : OGame actuel (chargé, daté, peu intuitif).

### Palette globale

```css
--void:    #050810   /* fond principal */
--panel:   rgba(13,18,30,0.85)   /* panneaux avec backdrop-filter blur */
--border:  rgba(35,50,70,0.8)
```

| Surface | Hex |
|---|---|
| surface (DEFAULT) | `#050810` |
| surface.secondary | `#0d1220` |
| surface.tertiary | `#131b2e` |
| surface.elevated | `#1a2540` |
| surface.border | `#1e2d45` |

### Couleurs accent

| Accent | Hex | Usage |
|---|---|---|
| blue | `#2d7dd2` | actions principales, focus, liens |
| violet | `#7c3aed` | éléments narratifs, Dérive |
| cyan | `#06b6d4` | informations, tooltips |
| green | `#10b981` | succès, validation |
| orange | `#f97316` | alertes douces |

### Couleurs ressources

```css
--metal:      #94a3b8   /* gris ardoise */
--crystal:    #7dd3fc   /* cyan clair */
--deuterium:  #86efac   /* vert tendre */
--energy:     #fbbf24   /* doré */
```

---

## 2. Palette de rareté (canon — respect absolu)

| Rareté | Hex | Tailwind | Effet spécial |
|---|---|---|---|
| COMMON | `#9E9E9E` | `text-gray-400 border-gray-500` | — |
| UNCOMMON | `#4CAF50` | `text-green-400 border-green-500` | — |
| RARE | `#2196F3` | `text-blue-400 border-blue-500` | — |
| EPIC | `#9C27B0` | `text-purple-400 border-purple-500` | — |
| LEGENDARY | `#FFD700` | `text-yellow-400 border-yellow-400` | Effet `glow-legendary` (double-layer 0.5+0.2 + animation `pulse-glow`) |

### Glow par rareté (CSS)

```css
.glow-common    { box-shadow: 0 0 8px rgba(158,158,158,0.30); }
.glow-uncommon  { box-shadow: 0 0 8px rgba(76,175,80,0.35); }
.glow-rare      { box-shadow: 0 0 8px rgba(33,150,243,0.40); }
.glow-epic      { box-shadow: 0 0 8px rgba(156,39,176,0.45); }
.glow-legendary {
  box-shadow: 0 0 12px #FFD70066, 0 0 24px #FFD70033;
  animation: pulse-glow 2.5s infinite;
}
```

### Helper TS `rarityGlow(r)`

LEGENDARY → `'0 0 12px ${color}66, 0 0 24px ${color}33'`. Autres → `'0 0 8px ${color}44'`.

---

## 3. Typographie

| Famille | Fichier | Usage |
|---|---|---|
| **Orbitron** | Google Fonts (400/500/600/700/900) | Display, titres section, badges (uppercase letter-spacing 0.15em) |
| **Inter** | Google Fonts (300/400/500/600/700) | Texte courant, body, UI |
| **JetBrains Mono** | Google Fonts (400/500/600) | Stats numériques, code |

Tailwind alias : `font-display` (Orbitron), `font-sans` (Inter par défaut), `font-mono` (JetBrains Mono).

---

## 4. Animations clés

```css
@keyframes shimmer    { 0% { background-position: -200%; } 100% { background-position: 200%; } }
@keyframes pulse-glow { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }
@keyframes forge-burn { /* flicker opacity + brightness */ }
@keyframes slide-up   { from { translateY(10px); opacity: 0; } to { translateY(0); opacity: 1; } }
@keyframes fade-in    { 0% { opacity: 0; } 100% { opacity: 1; } }
@keyframes float      { 0%, 100% { translateY(0); } 50% { translateY(-6px); } }
@keyframes scan       { 0% { translateY(-100%); } 100% { translateY(400%); } }
@keyframes glow       { 0% { box-shadow: 0 0 5px; } 100% { box-shadow: 0 0 20px, 0 0 40px; } }
```

Durées :
- shimmer : 1.8 s infinite (loaders).
- pulse-glow : 2.5 s infinite (LEGENDARY).
- forge-burn : 2 s (forge active).
- slide-up : 0.25 s ease-out (entrées de panneaux).
- fade-in : 0.3 s.
- float : 4 s (vaisseaux qui flottent doucement).
- scan : 4 s linear (effet de scan sur cartes).
- glow : 2 s alternate.

---

## 5. Composants visuels structurels

### Panneaux

```
.panel        — bg-panel, border, rounded-xl, backdrop-filter blur(12px)
.panel-glass  — rgba(17,24,39,0.6) + blur(16px)
.panel-glow::before — top 1px line gradient blue 0.6 horizontal
```

### Boutons

| Class | Style |
|---|---|
| `.btn-primary` | gradient `#2d7dd2 → #1a5fa8`, shadow `0 0 20px rgba(45,125,210,0.3)` + inset highlight, hover lift -1px + shadow 30px / 0.5 |
| `.btn-secondary` | bg `rgba(28,35,51,0.8)`, hover gradient → `rgba(45,60,80,0.8)` |
| `.btn-danger` | text-red-400, border-red-800/60, bg `rgba(127,29,29,0.2)` |
| `.btn-ghost` | text-gray-400, hover white, no bg |

Tous : `:active { scale-95 }`.

### Inputs

```
.input-field — bg rgba(12,16,28,0.8), border rgba(45,58,80,0.8)
:focus       — border bleu accent + 3px glow ring
```

### Badges / stat bars

```
.badge        — rounded-full uppercase tracking-wider
.badge-rarity — letter-spacing 0.1em
.stat-bar     — h-1.5 rounded-full bg rgba(45,58,80,0.5)
.stat-bar-fill— rounded-full transition 700ms
```

### Bars de jauge (par stat)

| Class | Couleur |
|---|---|
| `.bar-hull` | gradient rouge |
| `.bar-shield` | gradient bleu |
| `.bar-xp` | gradient ambre |
| `.bar-metal` | gradient slate |
| `.bar-crystal` | gradient sky |
| `.bar-deut` | gradient green |

---

## 6. Background décoratif

`body::before` : pseudo-élément fixed avec **10 étoiles aléatoires** en radial-gradient (opacités 0.15 à 0.6, coordonnées variées). `pointer-events: none, z-index: 0`.

Background body : superposition de 3 radial gradients :
- ellipse 80%/50% à 20%/-10% — bleu `rgba(45,125,210,0.12)` → transparent.
- ellipse 60%/40% à 80%/100% — violet `rgba(124,58,237,0.08)`.
- ellipse 100%/100% à 50%/50% — cyan `rgba(6,182,212,0.03)`.

Scrollbar custom : 4 px, track transparent, thumb `rgba(45,125,210,0.4)` rounded 2 px, hover 0.8.

---

## 7. Catalogue des écrans

| Écran | Route | Statut design | Statut implémentation |
|---|---|---|---|
| Login / Register | `/login` | FAIT | FAIT (dual-form, fond étoilé animé) |
| Dashboard | `/dashboard` | FAIT | FAIT (resources live, fleet active, forge en cours, daily) |
| Planète (détail) | `/planets/:id` | FAIT | FAIT (interpolation ressources, queue construction) |
| Bâtiments | `/buildings` | FAIT | FAIT (BuildingTooltip enrichi) |
| Hangar | `/hangar` | FAIT | FAIT (filtres rareté/classe/status, modal build) |
| Détail vaisseau | `/hangar/:id` | FAIT | FAIT (stats, modules, pedigree, scars, missions, traits) |
| Forge | `/forge` | FAIT | FAIT (ForgeProgress + countdown + Dérive badge) |
| Carte galactique | `/galaxy` | FAIT | FAIT (`GalaxyMap.tsx`, sélecteur galaxie/système) |
| Technologies | `/tech` | FAIT | FAIT (arbre par classe, prérequis visuels) |
| Expéditions | `/expeditions` | FAIT | FAIT (sélection durée, résultat, historique) |
| Classement | `/ranking` | FAIT | FAIT (top 100, position perso, refetch 60 s) |
| Combats (liste) | `/combat` | FAIT | FAIT |
| Combat report | `/combat/:id` | FAIT | FAIT (animation rounds) |
| Alliances | `/alliances` | FAIT | FAIT (top 50, détail, membres, guerres) |
| Profil joueur | — | À FAIRE | À FAIRE |
| Notifications | (overlay) | FAIT | FAIT (`NotificationPanel.tsx` connecté au WS) |

---

## 8. Composants réutilisables (catalogue)

### Vaisseaux
- **`<ShipCard>`** : carte vaisseau dans grille, classe + rareté coloré, grade indicator, status badge. Hover lift -2px.
- **`<ShipStatPanel>`** : stats comparées base vs current, mention `cap_reached` (icône 🔒 ou bordure rouge).
- **`<RarityReveal>`** : animation overlay au build d'un vaisseau RARE+ (révèle la rareté en grand).
- **`<SpectreAwakening>`** : overlay full-screen au passage Grade 5, autonome, déclenché via `gameStore.spectreData`.

### Planètes
- **`<ResourceBar>`** : métal/cristal/deutérium en temps réel avec interpolation côté client. Stocke base + rate, recalcule à chaque tick.

### Galaxie
- **`<GalaxyMap>`** : composant interactif de la carte galactique (15 slots orbitaux, sélection de cible).

### Combat
- **`<CombatReport>`** : rapport détaillé (rounds, XP gagnée, pertes, cicatrices, synergies). Overlay full-screen monté dans AppLayout.

### Bâtiments
- **`<BuildingCardUX>`** : carte bâtiment enrichie (label, description, prochain unlock, synergies, tip).
- **`<BuildingTooltip>`** : tooltip enrichi sur survol (description complète, bonus par niveau, prérequis).

### Daily
- **`<DailyPanel>`** : streak cycle 7 jours, missions du jour avec progression, claim button.

### Forge
- **`<ForgeProgress>`** : barre de progression + countdown via `useCountdown(eta_seconds)`. Marque `is_drift` si dérivée.

### Layout
- **`<AppLayout>`** : navigation principale, sidebar, monte 2 overlays globaux (`CombatReport`, `SpectreAwakening`), active `useGameSocket()`.
- **`<NotificationPanel>`** : panneau coulissant des notifications WS, point rouge sur cloche s'il y a des unread.

### UI library (`components/ui/index.tsx`)
`Badge`, `Modal`, `Tabs`, `Skeleton`, `EmptyState`, `LoadingSpinner`.

---

## 9. États globaux & flows UX

### Flow build vaisseau

```
1. User clique "Construire" sur HangarPage
2. Modal avec sélecteur ship_type + sélecteur planet_id + (opt) parent_ship_id Pedigree
3. Submit → POST /ships/build
4. Réponse 201 :
   - Si rareté ≥ RARE : <RarityReveal> animation 2s
   - Toast succès
   - Invalidate query /ships
5. Vaisseau apparaît en DOCKED dans le hangar
```

### Flow combat

```
1. Joueur attaque depuis GalaxyPage → POST /fleets (ATTACK)
2. UI : flotte apparaît dans /fleets active avec arrives_at
3. Server : fleet_arrival 5s détecte arrivée → combat_engine.resolve_combat
4. WS combat.result reçu côté client (attaquant ET défenseur)
5. <CombatReport> overlay s'ouvre, affiche rounds animés
6. Si grade_up Grade 5 : <SpectreAwakening> overlay enchaîné
7. Toast pour chaque cicatrice gagnée
8. Invalidate query /ships, /planets, /combat/history
```

### Flow forge

```
1. ForgePage : sélection 2 ships même type/rareté (UI filtre auto)
2. POST /forge → 201 + ForgeStatusResponse
3. <ForgeProgress> avec countdown 8h
4. WS forge.complete reçu après 8h → toast enrichi (nom + trait + drift)
5. Si is_drift : badge violet pâle + bordure pointillé sur le nouveau ship
6. Invalidate /forge/history et /ships
```

### Flow expédition

```
1. ExpeditionPage : sélection 1-5 ships + durée (2h/6h/12h)
2. POST /expeditions/launch → 201
3. UI affiche expé en cours (Redis-backed, survit redémarrage)
4. Au retour automatique (resolve_expedition côté serveur) :
   - resources gagnées (capées par capacity)
   - XP au lead_ship (max grade/xp)
   - module drop si event Bon (pas encore persisté)
   - cicatrice si event Difficile/Exceptionnel
5. UI : panneau résultat narratif + invalidate /ships
```

---

## 10. Règles UX absolues

1. **`current_stats` n'est jamais calculé côté client.** Toujours utiliser ce que retourne `GET /ships/:id`.
2. **Après un event WS** (`combat.result`, `forge.complete`, `ship.grade_up`, etc.) : **invalider les queries TanStack** concernées pour forcer un refetch.
3. **La rareté est lue depuis l'API**, jamais inférée d'autres champs.
4. **Les countdowns** s'interpolent côté client (`eta_seconds → useCountdown`), mais `GET /forge/:id` reste la source de vérité (utilisé en fallback si WS coupé).
5. **`cap_reached`** : si une stat est dans ce tableau, afficher un indicateur visuel (icône 🔒 ou bordure rouge) pour informer que le cap +150 % est atteint.
6. **Mobile-first** : tous les composants doivent fonctionner sur écran 375 px+.
7. **Pas de pop-ups intrusifs** — sidepanels, overlays doux, modals discrètes.
8. **Animations subtiles, pas lourdes.** Aucune animation > 2 s sauf overlays narratifs (RarityReveal, SpectreAwakening).
9. **Lisibilité prioritaire** sur l'esthétique. Pas de texte ≤ 12 px, contraste WCAG AA minimum.

---

## 11. Configuration UI (constantes du frontend)

### `RARITY_CONFIG`

```ts
COMMON:    { color: '#9E9E9E', label: 'Commun',     tw: 'text-gray-400 border-gray-500' }
UNCOMMON:  { color: '#4CAF50', label: 'Peu commun', tw: 'text-green-400 border-green-500' }
RARE:      { color: '#2196F3', label: 'Rare',       tw: 'text-blue-400 border-blue-500' }
EPIC:      { color: '#9C27B0', label: 'Épique',     tw: 'text-purple-400 border-purple-500' }
LEGENDARY: { color: '#FFD700', label: 'Légendaire', tw: 'text-yellow-400 border-yellow-400' }
```

### `GRADE_CONFIG`

```ts
0: { name: 'Recrue',   xp: 0 }
1: { name: 'Vétéran',  xp: 500 }
2: { name: 'Élite',    xp: 2000 }
3: { name: 'Légion',   xp: 6000 }
4: { name: 'Légende',  xp: 15000 }
5: { name: 'Spectre',  xp: 40000 }
```

### `SHIP_TYPE_CONFIG`

```ts
frigate_attack:      { icon: '⚔️', class: 'ATTACK' }
frigate_defense:     { icon: '🛡️', class: 'DEFENSE' }
frigate_support:     { icon: '💊', class: 'SUPPORT' }
frigate_exploration: { icon: '🔭', class: 'EXPLORATION' }
cruiser_attack:      { icon: '⚔️', class: 'ATTACK' }
cruiser_defense:     { icon: '🛡️', class: 'DEFENSE' }
```

### `MODULE_CONFIG`

```ts
PROPELLER: { stat: 'speed',        icon: '🚀' }
ARMOR:     { stat: 'hull',         icon: '🔩' }
CANNON:    { stat: 'dps',          icon: '💥' }
EMITTER:   { stat: 'support_aura', icon: '📡' }
SHIELD:    { stat: 'shield',       icon: '🛡️' }
CARGO:     { stat: 'cargo',        icon: '📦' }
```

---

## 12. Toast notifications (react-hot-toast)

Position `top-right`. Style par défaut :
- `background: '#1c2333'`
- `color: '#fff'`
- `border: '1px solid #2d3a50'`
- `borderRadius: '8px'`

Themes :
- success : icon `#4CAF50` sur `#fff`.
- error : icon `#ef4444` sur `#fff`.

---

## 13. Améliorations UI à prévoir

| Tâche | Priorité |
|---|---|
| Page Profil joueur (stats globales, historique combats, alliance, vaisseaux) | Moyenne |
| Animations skins / cosmétiques pour vaisseaux | Basse |
| Flow onboarding / tutoriel premier joueur (ouverture Phase 2) | Haute |
| Améliorer NotificationPanel (groupement par type, priorités, sticky) | Moyenne |
| Animations de combat plus poussées (rounds, vaisseaux qui explosent) | Basse |
| Affichage Pedigree dans ShipDetail (mention du parent) | Moyenne |
| Tooltip narratif sur cicatrices au survol | Moyenne |
| Page espionnage (Phase 2) | Phase 2 |
| Page marché galactique (Phase 2) | Phase 2 |

---

*Document Agent 4 — Mai 2026*
