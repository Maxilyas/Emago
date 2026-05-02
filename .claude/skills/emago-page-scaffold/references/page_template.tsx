/**
 * frontend/src/pages/<Name>Page.tsx
 *
 * Template page React/TypeScript Emago.
 * Patterns intégrés :
 * - TanStack Query (cache + refetch interval)
 * - Zustand stores (auth, game)
 * - lib/api.ts (silent refresh sur 401)
 * - react-hot-toast pour erreurs
 * - Tailwind classes design system Emago
 * - Animations animate-fade-in / animate-slide-up
 * - Mobile-first 375px+
 *
 * Adapte les éléments {…} pour ton cas d'usage.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';

import { useAuthStore } from '@/stores/authStore';
import { useGameStore } from '@/stores/gameStore';
import { api, ApiError } from '@/lib/api';
import {
  LoadingSpinner,
  EmptyState,
  Modal,
  Badge,
  Tabs,
  Skeleton,
} from '@/components/ui';
import { fmt, fmtCountdown, rarityColor, rarityGlow } from '@/lib/utils';
import { RARITY_CONFIG, type Rarity, type ShipSummary } from '@/types';
import toast from 'react-hot-toast';


// ─────────────────────────────────────────────────────────────────────────────
// Types locaux (si ad hoc à la page — sinon les externaliser dans @/types)
// ─────────────────────────────────────────────────────────────────────────────

interface XxxItem {
  id: string;
  name: string;
  // … champs spécifiques
}

interface CreateXxxRequest {
  // … schema body POST
}


// ─────────────────────────────────────────────────────────────────────────────
// Sous-composants inline (extraire si réutilisés ailleurs)
// ─────────────────────────────────────────────────────────────────────────────

function XxxCard({ item, onSelect }: { item: XxxItem; onSelect?: (id: string) => void }) {
  return (
    <button
      onClick={() => onSelect?.(item.id)}
      className="panel p-4 hover:border-accent-blue/40 transition-all hover:-translate-y-0.5 text-left"
    >
      <h3 className="font-display uppercase tracking-wide text-sm text-white">{item.name}</h3>
      {/* … */}
    </button>
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// Page principale
// ─────────────────────────────────────────────────────────────────────────────

export default function XxxPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { username } = useAuthStore();

  // State local
  const [tab, setTab] = useState<'list' | 'history'>('list');
  const [showCreate, setShowCreate] = useState(false);

  // ─── Queries ────────────────────────────────────────────────────────────────
  const { data: items = [], isLoading: itemsLoading } = useQuery({
    queryKey: ['xxx'],
    queryFn: () => api.get<XxxItem[]>('/xxx'),
    refetchInterval: 30_000,  // 30s par défaut. Adapter : 10s pour fleets/expeditions, 60s pour ranking
  });

  // Query conditionnelle (enabled si tab actif)
  const { data: history = [] } = useQuery({
    queryKey: ['xxx-history'],
    queryFn: () => api.get<XxxItem[]>('/xxx/history'),
    enabled: tab === 'history',
    refetchInterval: 60_000,
  });

  // ─── Mutations ──────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (body: CreateXxxRequest) => api.post<XxxItem>('/xxx', body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['xxx'] });
      toast.success('Création réussie');
      setShowCreate(false);
    },
    onError: (err: ApiError | Error) => {
      const msg = err instanceof ApiError ? err.detail : 'Erreur serveur';
      toast.error(msg);
    },
  });

  // ─── Loading state ──────────────────────────────────────────────────────────
  if (itemsLoading) {
    return (
      <div className="animate-fade-in space-y-4">
        <header className="flex items-center justify-between">
          <h1 className="font-display uppercase tracking-wide text-2xl text-white">Xxx</h1>
        </header>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="font-display uppercase tracking-wide text-2xl text-white">Xxx</h1>
          <p className="text-sm text-gray-400 mt-1">Sous-titre descriptif.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary"
        >
          + Créer
        </button>
      </header>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['list', 'history'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t
                ? 'bg-accent-blue text-white'
                : 'bg-surface-secondary text-gray-400 hover:text-white'
            }`}
          >
            {t === 'list' ? 'Actifs' : 'Historique'}
          </button>
        ))}
      </div>

      {/* Empty state */}
      {tab === 'list' && items.length === 0 && (
        <EmptyState
          icon="📭"
          title="Aucun élément"
          message="Lance ton premier xxx pour démarrer."
          cta={
            <button onClick={() => setShowCreate(true)} className="btn-primary mt-4">
              + Créer
            </button>
          }
        />
      )}

      {/* Grid responsive */}
      {tab === 'list' && items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <XxxCard
              key={item.id}
              item={item}
              onSelect={(id) => navigate(`/xxx/${id}`)}
            />
          ))}
        </div>
      )}

      {/* Section history */}
      {tab === 'history' && (
        <section className="panel p-4 space-y-2">
          {history.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">Aucun historique.</p>
          ) : (
            history.map((h) => (
              <div key={h.id} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                <span>{h.name}</span>
                <Link to={`/xxx/${h.id}`} className="text-accent-blue hover:underline text-sm">
                  Voir
                </Link>
              </div>
            ))
          )}
        </section>
      )}

      {/* Modal création */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)}>
        <div className="panel-glass animate-slide-up p-6 max-w-md w-full">
          <h2 className="font-display uppercase tracking-wide text-lg text-white mb-4">
            Nouveau Xxx
          </h2>

          {/* Formulaire ici — utilise input-field, btn-primary, btn-ghost */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate({
                // … body
              });
            }}
            className="space-y-4"
          >
            <label className="block">
              <span className="text-sm text-gray-400">Nom</span>
              <input
                type="text"
                className="input-field w-full mt-1"
                required
              />
            </label>

            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="btn-ghost"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="btn-primary"
              >
                {createMutation.isPending ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Création…
                  </span>
                ) : (
                  'Créer'
                )}
              </button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}
