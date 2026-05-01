/**
 * pages/AlliancesPage.tsx
 * Agent 6 — Développeur Frontend | Sprint 4
 * Design : Agent 4 — UI/UX
 *
 * Page Alliances : liste, recherche, création, détail.
 * Consomme GET /api/v1/alliances, POST /api/v1/alliances, etc.
 */
import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { LoadingSpinner, EmptyState, Modal, Badge } from '@/components/ui'
import { fmt, fmtDate } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'

// ─── Types ────────────────────────────────────────────────────────────────────

interface AllianceSummary {
  id: string
  name: string
  tag: string
  score: number
  member_count: number
  leader_username: string
}

interface AllianceMember {
  player_id: string
  username: string
  role: 'LEADER' | 'OFFICER' | 'MEMBER'
  score: number
  joined_at: string
}

interface AllianceDetail extends AllianceSummary {
  description: string | null
  leader_id: string
  members: AllianceMember[]
  active_wars: WarOut[]
  created_at: string
}

interface WarOut {
  war_id: string
  opponent_name: string
  opponent_tag: string
  side: 'attacker' | 'defender'
  declared_at: string
  status: string
}

// ─── Palette rôles ───────────────────────────────────────────────────────────

const ROLE_CONFIG: Record<string, { label: string; color: string }> = {
  LEADER:  { label: 'Leader',   color: '#FFD700' },
  OFFICER: { label: 'Officier', color: '#9C27B0' },
  MEMBER:  { label: 'Membre',   color: '#9E9E9E' },
}

// ─── Composant création d'alliance ───────────────────────────────────────────

function CreateAllianceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const [tag, setTag] = useState('')
  const [desc, setDesc] = useState('')
  const qc = useQueryClient()

  const createMutation = useMutation({
    mutationFn: () => api.post('/alliances', { name, tag: tag.toUpperCase(), description: desc || null }).then(r => r.json()),
    onSuccess: () => {
      toast.success(`Alliance [${tag.toUpperCase()}] créée !`)
      qc.invalidateQueries({ queryKey: ['alliances'] })
      qc.invalidateQueries({ queryKey: ['my-alliance'] })
      onClose()
    },
    onError: (e: ApiError) => toast.error(e.detail || 'Erreur de création'),
  })

  return (
    <Modal open={open} onClose={onClose} title="Créer une alliance">
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Nom <span className="text-gray-500">(3-32 caractères)</span></label>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            maxLength={32}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            placeholder="Nom de l'alliance"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-300 mb-1">Tag <span className="text-gray-500">(2-5 lettres majuscules)</span></label>
          <input
            value={tag}
            onChange={e => setTag(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))}
            maxLength={5}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-blue-500"
            placeholder="NOVA"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-300 mb-1">Description <span className="text-gray-500">(optionnel)</span></label>
          <textarea
            value={desc}
            onChange={e => setDesc(e.target.value)}
            maxLength={500}
            rows={3}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm resize-none focus:outline-none focus:border-blue-500"
            placeholder="Décrivez votre alliance..."
          />
        </div>
        <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-lg p-3 text-xs text-yellow-300">
          Coût : 10 000 métal + 5 000 cristal (prélevés sur votre planète natale)
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white text-sm transition-colors">
            Annuler
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={name.length < 3 || tag.length < 2 || createMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors font-medium"
          >
            {createMutation.isPending ? 'Création...' : 'Créer'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ─── Composant détail alliance ────────────────────────────────────────────────

function AllianceDetailPanel({ alliance, onJoin }: { alliance: AllianceDetail; onJoin: (id: string) => void }) {
  const { playerId } = useAuthStore()
  const isMyAlliance = alliance.members.some(m => m.player_id === playerId)

  return (
    <div className="rounded-xl bg-gray-800/50 border border-gray-700 p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-yellow-300 font-mono font-bold text-lg">[{alliance.tag}]</span>
            <h2 className="text-xl font-bold text-white">{alliance.name}</h2>
          </div>
          {alliance.description && (
            <p className="text-gray-400 text-sm mt-1">{alliance.description}</p>
          )}
        </div>
        <div className="text-right shrink-0">
          <p className="text-white font-bold text-lg">{fmt(alliance.score)}</p>
          <p className="text-gray-400 text-xs">Score</p>
        </div>
      </div>

      {/* Guerres actives */}
      {alliance.active_wars.length > 0 && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-lg p-3">
          <p className="text-red-400 font-bold text-sm mb-2">⚔️ En guerre</p>
          {alliance.active_wars.map(w => (
            <p key={w.war_id} className="text-red-300 text-xs">
              {w.side === 'attacker' ? 'vs.' : 'défend contre'} [{w.opponent_tag}] {w.opponent_name}
            </p>
          ))}
        </div>
      )}

      {/* Membres */}
      <div>
        <h3 className="text-gray-300 font-medium text-sm mb-2">
          Membres ({alliance.members.length}/20)
        </h3>
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {alliance.members.sort((a, b) => {
            const order = { LEADER: 0, OFFICER: 1, MEMBER: 2 }
            return order[a.role] - order[b.role]
          }).map(m => (
            <div key={m.player_id} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-700/30">
              <div className="flex items-center gap-2">
                <span
                  className="text-xs font-bold"
                  style={{ color: ROLE_CONFIG[m.role]?.color || '#9E9E9E' }}
                >
                  {ROLE_CONFIG[m.role]?.label}
                </span>
                <span className="text-white text-sm">{m.username}</span>
              </div>
              <span className="text-gray-400 text-xs">{fmt(m.score)} pts</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action rejoindre */}
      {!isMyAlliance && alliance.members.length < 20 && (
        <button
          onClick={() => onJoin(alliance.id)}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg font-medium transition-colors"
        >
          Rejoindre cette alliance
        </button>
      )}
      {isMyAlliance && (
        <div className="text-center text-blue-400 text-sm py-1">✓ Vous êtes membre</div>
      )}
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function AlliancesPage() {
  const [selected, setSelected] = useState<AllianceDetail | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [search, setSearch] = useState('')
  const qc = useQueryClient()

  const { data: alliances, isLoading } = useQuery<AllianceSummary[]>({
    queryKey: ['alliances'],
    queryFn: () => api.get('/alliances').then(r => r.json()),
    refetchInterval: 60_000,
  })

  const joinMutation = useMutation({
    mutationFn: (allianceId: string) => api.post(`/alliances/${allianceId}/join`).then(r => r.json()),
    onSuccess: (data) => {
      toast.success(`Vous avez rejoint [${data.tag}] ${data.alliance_name} !`)
      qc.invalidateQueries({ queryKey: ['alliances'] })
      if (selected) setSelected({ ...selected, member_count: selected.member_count + 1 })
    },
    onError: (e: ApiError) => toast.error(e.detail || 'Impossible de rejoindre'),
  })

  const loadDetail = async (id: string) => {
    const detail = await api.get(`/alliances/${id}`).then(r => r.json())
    setSelected(detail)
  }

  const filtered = (alliances || []).filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.tag.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* En-tête */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-white font-display">Alliances</h1>
        <button
          onClick={() => setCreateOpen(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg font-medium transition-colors"
        >
          + Créer une alliance
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Liste */}
        <div className="space-y-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher par nom ou tag..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          />

          {isLoading ? (
            <LoadingSpinner />
          ) : filtered.length === 0 ? (
            <EmptyState title="Aucune alliance" description="Soyez le premier à en créer une !" />
          ) : (
            <div className="space-y-2">
              {filtered.map(a => (
                <button
                  key={a.id}
                  onClick={() => loadDetail(a.id)}
                  className={`w-full text-left rounded-xl p-4 border transition-all ${
                    selected?.id === a.id
                      ? 'bg-blue-900/30 border-blue-500'
                      : 'bg-gray-800/50 border-gray-700 hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-yellow-300 font-mono font-bold text-sm">[{a.tag}]</span>
                      <span className="text-white font-medium ml-2">{a.name}</span>
                    </div>
                    <span className="text-gray-400 text-xs">{a.member_count}/20</span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-gray-400 text-xs">Chef : {a.leader_username}</span>
                    <span className="text-gray-300 text-xs font-mono">{fmt(a.score)} pts</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Détail */}
        <div>
          {selected ? (
            <AllianceDetailPanel
              alliance={selected}
              onJoin={(id) => joinMutation.mutate(id)}
            />
          ) : (
            <div className="rounded-xl bg-gray-800/30 border border-gray-700/50 p-8 text-center">
              <p className="text-gray-500">Sélectionnez une alliance pour voir ses détails</p>
            </div>
          )}
        </div>
      </div>

      <CreateAllianceModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
