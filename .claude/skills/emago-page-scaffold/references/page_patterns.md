# Patterns de pages Emago

Conventions extraites des 14 pages existantes (`docs/06_dev_frontend.md` section 7).

## 1. Refetch intervals par type de page

| Page | refetchInterval | Raison |
|---|---:|---|
| Dashboard | 30 s | Vue globale, pas critique en temps réel |
| Planet detail | 15-30 s | Construction queue + ressources |
| Buildings | 15 s | Construction en temps quasi-réel |
| Hangar | (no refetch) | Invalidé sur events WS |
| Forge | 30 s + WS | Forge actives + history |
| Galaxy / fleets | 10 s | Flottes en transit, action urgente possible |
| Expeditions | 10 s | Détecter complétion |
| Tech | 30 s | Recherches longues |
| Ranking | 60 s | Pas critique |
| Alliances | 30-60 s | Actions assez rares |
| Combats | (no refetch) | Invalidé sur events WS |

## 2. Sous-composants inline vs extraits

**Inline (dans le fichier de la page)** quand :
- Couplage fort à la logique de la page (countdown spécifique, état partagé).
- Utilisé une seule fois dans tout le frontend.
- < 50 lignes JSX.

**Extrait (dans `components/<feature>/`)** quand :
- Réutilisé sur ≥ 2 pages.
- ≥ 50 lignes JSX.
- A son propre état complexe.
- A son propre type de props bien défini.

Exemples :
- `FleetCountdown` (inline dans `DashboardPage` ET `GalaxyPage`) — devrait probablement être extrait, candidat refacto.
- `ShipCard` — extrait, utilisé partout.
- `ResourceCounter` (inline dans `PlanetPage`) — couplé à la logique d'interpolation locale, OK inline.

## 3. Pattern countdown interpolé client

```tsx
function ItemCountdown({ etaSeconds, onComplete }: { etaSeconds: number; onComplete?: () => void }) {
  const [remaining, setRemaining] = useState(etaSeconds);
  const startedAt = useRef(Date.now());
  const completedRef = useRef(false);

  useEffect(() => {
    startedAt.current = Date.now();
    completedRef.current = false;
    setRemaining(etaSeconds);
  }, [etaSeconds]);

  useEffect(() => {
    const tick = () => {
      const elapsed = (Date.now() - startedAt.current) / 1000;
      const left = Math.max(0, etaSeconds - elapsed);
      setRemaining(Math.round(left));

      if (left <= 0 && !completedRef.current) {
        completedRef.current = true;
        onComplete?.();
      }
    };
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [etaSeconds, onComplete]);

  return <span className="font-mono">{fmtCountdown(remaining)}</span>;
}
```

OU utiliser le hook `useCountdown` du projet : `const { remaining, pct, done } = useCountdown(eta_seconds, onComplete)`.

## 4. Pattern interpolation ressources (Planet)

```tsx
function ResourceCounter({
  base,
  ratePerHour,
  capacity,
  updatedAt,
}: {
  base: number;
  ratePerHour: number;
  capacity: number;
  updatedAt: string;
}) {
  const [current, setCurrent] = useState(base);
  const baseRef = useRef(base);
  const startedAt = useRef(new Date(updatedAt).getTime());

  useEffect(() => {
    baseRef.current = base;
    startedAt.current = new Date(updatedAt).getTime();
  }, [base, updatedAt]);

  useEffect(() => {
    const tick = () => {
      const elapsedH = (Date.now() - startedAt.current) / (3600 * 1000);
      const next = Math.min(capacity, baseRef.current + ratePerHour * elapsedH);
      setCurrent(next);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [ratePerHour, capacity]);

  return <span>{fmt(current, 0)}</span>;
}
```

## 5. Pattern modal avec submit async

```tsx
const [showModal, setShowModal] = useState(false);
const [launching, setLaunching] = useState(false);

async function handleSubmit() {
  setLaunching(true);
  try {
    await createMutation.mutateAsync({ /* body */ });
    setShowModal(false);  // close on success
  } catch (e) {
    // toast déjà géré par onError de la mutation
  } finally {
    setLaunching(false);
  }
}

<Modal isOpen={showModal} onClose={() => setShowModal(false)}>
  <div className="panel-glass animate-slide-up p-6">
    {/* ... */}
    <button onClick={handleSubmit} disabled={launching} className="btn-primary">
      {launching ? <span className="...spinner..." /> : 'Lancer'}
    </button>
  </div>
</Modal>
```

## 6. Pattern filtres pilule (Hangar)

```tsx
const [statusFilter, setStatusFilter] = useState<'all' | 'DOCKED' | 'IN_FLEET' | 'IN_FORGE'>('all');
const [rarityFilter, setRarityFilter] = useState<Rarity | 'all'>('all');

const filteredShips = ships.filter((s) =>
  (statusFilter === 'all' || s.status === statusFilter) &&
  (rarityFilter === 'all' || s.rarity === rarityFilter)
);

// Render :
<div className="flex gap-2 flex-wrap">
  {(['all', 'DOCKED', 'IN_FLEET', 'IN_FORGE'] as const).map((s) => (
    <button
      key={s}
      onClick={() => setStatusFilter(s)}
      className={statusFilter === s ? 'badge bg-accent-blue text-white' : 'badge bg-surface-secondary'}
    >
      {s}
    </button>
  ))}
</div>
```

## 7. Pattern grid responsive

```tsx
// 1 col mobile, 2 cols tablet, 3 cols desktop
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(...)}
</div>

// 1 col mobile, 2 cols ≥ 640px (sm)
<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
```

## 8. Pattern WS handler ↔ invalidate

Les WS events sont gérés globalement dans `useWsEventHandlers()` (depuis `NotificationPanel`), branchés via `useGameSocket` (instancié au niveau `AppLayout`). Une page n'instancie JAMAIS son propre `useGameSocket`.

Pour qu'une page réagisse à un event WS :
- Le handler dans `useWsEventHandlers` invalide la query concernée.
- La page utilise cette query → refetch automatique.

Exemple :
```tsx
// Dans NotificationPanel.tsx
const handleEspionageReportReady = (data: EspionageReportData) => {
  qc.invalidateQueries({ queryKey: ['espionage-reports'] });
  toast.success(`Rapport d'espionnage reçu : ${data.target_username}`);
};

// Dans EspionagePage.tsx — rien de spécial, juste utiliser la query :
const { data: reports } = useQuery({
  queryKey: ['espionage-reports'],
  queryFn: () => api.get('/espionage/reports'),
});
```

## 9. Pattern conditional rendering avec early returns

```tsx
if (isLoading) return <LoadingSpinner />;
if (error) return <ErrorState message={error.message} />;
if (!data?.length) return <EmptyState ... />;

// Render normal :
return (...)
```

## 10. Pattern avec `useNavigate`

```tsx
import { useNavigate } from 'react-router-dom';

function MyPage() {
  const navigate = useNavigate();

  return (
    <button onClick={() => navigate('/hangar')}>Voir le hangar</button>
  );
}
```

## 11. Pattern partage state via gameStore (overlays globaux)

Pour déclencher un overlay full-screen depuis n'importe quelle page :

```tsx
// Dans la page :
const setSpectreData = useGameStore((s) => s.setSpectreData);

// Sur event :
setSpectreData({
  ship_id: '...',
  new_grade: 5,
  // ...
});
// L'overlay <SpectreAwakening> dans AppLayout réagit et s'ouvre.
```

## 12. Anti-patterns à éviter

- ❌ Calcul de `current_stats` côté client. **Toujours** afficher ce que retourne l'API.
- ❌ `useEffect + fetch` au lieu de `useQuery`.
- ❌ State local pour des données serveur (ça doit être dans TanStack Query).
- ❌ Refetch manuel via `setInterval` — utilise `refetchInterval` de TanStack Query.
- ❌ Multiple `useGameSocket()` dans plusieurs pages — instance unique au niveau AppLayout.
- ❌ Inférer la rareté côté client à partir de stats — toujours lire `RARITY_CONFIG[ship.rarity]`.
- ❌ Setter manuellement le cache après mutation — `invalidateQueries` est plus sûr.
- ❌ Rendu du JSX en prose sans className — toujours utiliser le design system.
