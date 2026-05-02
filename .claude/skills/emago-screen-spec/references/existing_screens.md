# Catalogue des 14 écrans Emago existants

Pour s'aligner sur les patterns établis. Détails dans `docs/06_dev_frontend.md` section 7.

| Écran | Route | Pattern de layout | À retenir |
|---|---|---|---|
| Login / Register | `/login` | Hero centré + tabs login/register, fond étoilé décoratif | Animation fade-in + translate-y au mount |
| Dashboard | `/dashboard` | Header username + rang ; sections : DailyPanel + planète natale + 4 stats empire + flottes en transit + forges + activité récente | DailyPanel mode `compact`, refetch 30s, FleetCountdown 1s |
| Planète détail | `/planets/:id` | ResourceBar + buildings grid + queue construction | ResourceCounter interpolation 1s base + rate × elapsed h, capé capacity |
| Bâtiments | `/buildings` | Sélecteur planète + sections (en construction / énergie / production / chantier / recherche / expéditions) | EnergyGauge avec consommation par mine, BuildingCardUX enrichi |
| Hangar | `/hangar` | Header + bouton "Construire" + filtres (status, rareté) + grid ShipCard | BuildModal plein écran, RarityReveal animé sur build success |
| Détail vaisseau | `/hangar/:id` | Card vaisseau + tabs Stats / Modules / Cicatrices | ModuleManager grid slots premium dashed jaune, démolition avec confirm() |
| Forge | `/forge` | Tabs Forge / Historique. Forge: 2 panels A/B + aperçu animé rareté ×2 → suivante | Filtre compatibilité same type AND same rarity, badge rareté animé pulse + glow |
| Carte galactique | `/galaxy` | Sélecteur galaxie/système + GalaxyMap SVG + listes flottes transit + flottes ennemies | GalaxyMap SVG interactif 15 slots orbitaux |
| Technologies | `/tech` | Bandeau recherche active + sélecteur 4 classes + grid TechCard | Désaturation si prérequis non remplis |
| Expéditions | `/expeditions` | Lancement (durée + ships) + reports retour | EVENT_ICONS mapping 12 events |
| Classement | `/ranking` | Top 100 + position perso highlightée | refetch 60s |
| Alliances | `/alliances` | Liste top 50 + détail (membres, guerres) | Validation tag uppercase 2-5 chars |
| Combats (liste) | `/combat` | Historique 50 derniers, lignes cliquables | Navigate vers `/combat/:id` |
| Combat report | `/combat/:id` | Réutilise `<CombatReport>` | Rounds animés |

## Patterns transversaux

### Header de page

```tsx
<header className="flex items-center justify-between mb-6">
  <h1 className="font-display uppercase tracking-wide text-2xl">Titre</h1>
  <button className="btn-primary">Action principale</button>
</header>
```

### État chargement

```tsx
if (isLoading) return <LoadingSpinner />;
// OU pour une grid : afficher des skeletons
{isLoading ? Array.from({length: 6}).map((_, i) => <ShipCardSkeleton key={i}/>) : ...}
```

### État vide

```tsx
<EmptyState
  icon="📭"
  title="Aucun élément"
  message="Cliquez sur Créer pour démarrer."
  cta={<button className="btn-primary">Créer</button>}
/>
```

### État erreur (toast)

```tsx
const mutation = useMutation({
  mutationFn: ...,
  onSuccess: () => { qc.invalidateQueries(...); toast.success('Action réussie'); },
  onError: (err: any) => toast.error(err.detail ?? 'Erreur serveur'),
});
```

### Filtres en pilule

```tsx
{['all', 'DOCKED', 'IN_FLEET', 'IN_FORGE'].map(s => (
  <button
    key={s}
    onClick={() => setStatusFilter(s)}
    className={`badge ${statusFilter === s ? 'bg-accent-blue text-white' : 'bg-surface-secondary text-gray-400'}`}
  >
    {s} <span className="ml-2">{counts[s]}</span>
  </button>
))}
```

### Grid responsive

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(...)}
</div>
```

### Modal / overlay

```tsx
<Modal isOpen={open} onClose={() => setOpen(false)}>
  <div className="panel-glass animate-slide-up p-6">
    ...
  </div>
</Modal>
```

## Catalogue des composants existants

Classés par dossier `frontend/src/components/`.

### `ships/`
- `<ShipCard>` — carte vaisseau pour grilles. Modes `compact`, `selected`. Glow par rareté. Hover lift -2px.
- `<ShipStatPanel>` — stats compared base vs current. Indicator `cap_reached`.
- `<RarityReveal>` — overlay révélation rareté nouveau ship (RARE+).
- `<SpectreAwakening>` — overlay full-screen Grade 5 atteint.

### `planets/`
- `<ResourceBar>` — métal/cristal/deutérium avec interpolation client.

### `galaxy/`
- `<GalaxyMap>` — SVG interactif 15 slots orbitaux.

### `combat/`
- `<CombatReport>` — rapport combat (rounds animés, XP, pertes, scars).

### `buildings/`
- `<BuildingCardUX>` — carte bâtiment enrichie avec accordion.
- `<BuildingTooltip>` — tooltip riche au survol.

### `daily/`
- `<DailyPanel>` — streak 7 jours + 3 missions. Mode `compact`.

### `forge/`
- `<ForgeProgress>` — barre + countdown via `useCountdown`. Badge `is_drift`.

### `layout/`
- `<AppLayout>` — navigation principale, monte overlays globaux, active `useGameSocket`.
- `<NotificationPanel>` — panneau notifications WS, dot rouge unread.

### `ui/` (lib utilitaire)
- `<Badge>`, `<Modal>`, `<Tabs>`, `<Skeleton>`, `<EmptyState>`, `<LoadingSpinner>`.
