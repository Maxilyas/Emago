# Composants Emago — quand quoi utiliser

Cheatsheet rapide pour choisir le bon composant lors d'une spec d'écran.

## Décision : "j'ai besoin d'afficher…"

| Besoin | Composant existant à utiliser | Note |
|---|---|---|
| Un vaisseau (carte courte) | `<ShipCard>` | Modes `compact`, `selected` |
| Stats détaillées d'un vaisseau | `<ShipStatPanel>` | base vs current, cap_reached |
| Animation révélation build RARE+ | `<RarityReveal>` | Overlay 2s |
| Animation Grade 5 atteint | `<SpectreAwakening>` | Overlay full-screen |
| Métal/cristal/deutérium temps réel | `<ResourceBar>` | Interpolation 1s |
| Carte d'un système (15 slots) | `<GalaxyMap>` | SVG interactif |
| Rapport de combat | `<CombatReport>` | Plein écran ou inline |
| Carte d'un bâtiment | `<BuildingCardUX>` | Avec accordion détails |
| Tooltip détaillé bâtiment | `<BuildingTooltip>` | Hover only |
| Progress forge (8h) | `<ForgeProgress>` | Avec useCountdown |
| Daily login + missions | `<DailyPanel>` | Mode `compact` ou full |
| Notifications | `<NotificationPanel>` | Sidebar coulissante |
| Badge générique | `<Badge>` | Rarity, status, count |
| Modal | `<Modal>` | Avec animation slide-up |
| Tabs | `<Tabs>` | Stats / Modules / Scars pattern |
| Skeleton loading | `<Skeleton>` | Shape via classes |
| Liste vide avec CTA | `<EmptyState>` | icon + title + msg + cta |
| Spinner full-screen | `<LoadingSpinner>` | À éviter si possible |

## Quand créer un nouveau composant

Critères pour justifier un nouveau composant :

- ☐ Réutilisé sur ≥ 2 pages.
- ☐ ≥ 50 lignes JSX.
- ☐ Logique de state interne non triviale.
- ☐ Animation ou effet propre.

Sinon, mieux vaut inliner dans la page (cf. patterns `ResourceCounter` inline dans `PlanetPage.tsx`, `FleetCountdown` inline dans `DashboardPage.tsx`/`GalaxyPage.tsx`).

## Conventions de nommage

| Type | Pattern | Exemple |
|---|---|---|
| Card de domaine | `<XxxCard>` | `ShipCard`, `BuildingCardUX` |
| Panel d'aperçu | `<XxxPanel>` | `DailyPanel`, `ShipStatPanel` |
| Progress / countdown | `<XxxProgress>` ou `<XxxCountdown>` | `ForgeProgress` |
| Overlay narratif | `<XxxReveal>` ou `<XxxAwakening>` | `RarityReveal`, `SpectreAwakening` |
| Bar de stat | `<XxxBar>` | `ResourceBar` |
| Map / vue spatiale | `<XxxMap>` | `GalaxyMap` |
| Tooltip | `<XxxTooltip>` | `BuildingTooltip` |
| Layout structurel | `<XxxLayout>` | `AppLayout` |

## Patterns d'extension

Si on doit ajouter un composant proche d'un existant :

- Plutôt que dupliquer, **ajouter un mode** au composant existant (cf. `ShipCard` modes `compact`, `selected`).
- Si trop de variations → extraire base + variants (cf. shadcn-ui pattern, mais pas encore en place sur Emago).

## Exemples par cas d'usage

### Liste filtrable (Hangar pattern)

```
[Filtres pilules]
[Bouton +Créer]
<grid responsive>
  {items.map(<ShipCard onClick={navigate /...:id}>)}
</grid>
[<EmptyState> si vide]
```

### Détail avec tabs (ShipDetail pattern)

```
[Header ← retour + actions]
[<Hero>: badge rareté + glow + name + ship_class + status + grade★]
<Tabs>
  Stats  → <ShipStatPanel>
  Modules → <ModuleManager>
  Scars   → <list scars>
</Tabs>
```

### Progression temps réel (Forge pattern)

```
[Sélection 2 panels A / B + ShipCard compact]
[Aperçu résultat avec animate-pulse]
[Bouton "Lancer" avec spinner pendant launching]
[Section Historique avec ForgeProgress pour active]
```

### Overlay narratif (Combat / Spectre pattern)

```
Déclenché par WS event → setSpectreData(data) ou setPendingCombatResult(data) dans gameStore
Monté au niveau AppLayout (jamais dans une page spécifique)
Animation full-screen, dismissable
Au dismiss → invalidateQueries + clear from store
```
