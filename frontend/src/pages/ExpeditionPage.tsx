import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { shipsApi } from '@/api/ships'
import { fmtCountdown, fmt } from '@/lib/utils'
import { LoadingSpinner } from '@/components/ui'
import { RARITY_CONFIG, type Rarity } from '@/types'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Expedition {
  expedition_id: string; ship_ids: string[]
  duration: 'SHORT' | 'MEDIUM' | 'LONG'
  launched_at: string; returns_at: string
  eta_seconds: number; is_complete: boolean
  result: ExpeditionResult | null
}

interface ExpeditionResult {
  expedition_id: string; event_id: string
  title: string; narrative: string
  resources_gained: Record<string, number>
  xp_gained: Record<string, number>
  modules_found: Array<{ type: string; level: number }>
  scars_earned: Array<{ ship_id: string; tag: string }>
  deuterium_lost?: number
}

// ─── Config durées ────────────────────────────────────────────────────────────
const DURATION_CONFIG = {
  SHORT:  { label: '2 heures',  icon: '⚡', color: '#10b981', risk: 'Faible',  deuterium: 500,  desc: 'Secteur proche. Ressources modestes, risque minimal.' },
  MEDIUM: { label: '6 heures',  icon: '🌟', color: '#2d7dd2', risk: 'Moyen',   deuterium: 1500, desc: 'Secteur intermédiaire. Bon équilibre risque/récompense.' },
  LONG:   { label: '12 heures', icon: '🌌', color: '#7c3aed', risk: 'Élevé',   deuterium: 4000, desc: 'Secteur lointain. Modules rares possibles, événements exceptionnels.' },
}

// ─── Countdown ────────────────────────────────────────────────────────────────
function ExpCountdown({ eta, onComplete }: { eta: number; onComplete: () => void }) {
  const [s, setS] = useState(eta)
  useEffect(() => {
    setS(eta); if (eta <= 0) { onComplete(); return }
    const start = Date.now()
    const id = setInterval(() => {
      const left = Math.max(0, eta - (Date.now() - start) / 1000)
      setS(Math.round(left)); if (left <= 0) { clearInterval(id); onComplete() }
    }, 1000)
    return () => clearInterval(id)
  }, [eta])
  if (s <= 0) return <span className="text-green-400 font-display font-bold">RETOUR !</span>
  const h = String(Math.floor(s/3600)).padStart(2,'0')
  const m = String(Math.floor((s%3600)/60)).padStart(2,'0')
  const sec = String(s%60).padStart(2,'0')
  return <span className="font-mono text-xl font-bold text-white">{h}:{m}:{sec}</span>
}

// ─── Rapport de résultat ──────────────────────────────────────────────────────
function ExpeditionReport({ result }: { result: ExpeditionResult }) {
  const isGood = result.resources_gained && Object.keys(result.resources_gained).length > 0
  const hasMod  = result.modules_found.length > 0
  const hasScar = result.scars_earned.length > 0

  const EVENT_ICONS: Record<string, string> = {
    debris_field: '🪐', alien_artifact: '👾', derelict_station: '🛸',
    rogue_freighter: '📦', void_storm: '🌀', strange_signal: '📡',
    navigation_error: '🧭', pirate_ambush: '⚔️', radiation_zone: '☢️',
    patrol_encounter: '🚨', legendary_wreck: '💎', first_contact: '🌌',
  }

  return (
    <div className="rounded-xl overflow-hidden border border-surface-border animate-slide-up">
      {/* Header événement */}
      <div className="p-4 flex items-center gap-3"
        style={{ background: 'linear-gradient(135deg, rgba(45,125,210,0.1), rgba(13,18,30,0.95))' }}>
        <span className="text-3xl">{EVENT_ICONS[result.event_id] ?? '🚀'}</span>
        <div>
          <p className="font-bold text-white">{result.title}</p>
          <p className="text-xs text-gray-400 mt-0.5 italic">"{result.narrative}"</p>
        </div>
      </div>

      <div className="p-4 space-y-3">
        {/* Ressources */}
        {isGood && (
          <div className="flex flex-wrap gap-3 text-sm">
            {result.resources_gained.metal && <span className="text-metal">⛏️ +{fmt(result.resources_gained.metal)}</span>}
            {result.resources_gained.crystal && <span className="text-crystal">💎 +{fmt(result.resources_gained.crystal)}</span>}
            {result.resources_gained.deuterium && <span className="text-deuterium">⚗️ +{fmt(result.resources_gained.deuterium)}</span>}
          </div>
        )}

        {/* XP */}
        {Object.keys(result.xp_gained).length > 0 && (
          <div className="text-sm">
            {Object.entries(result.xp_gained).map(([shipId, xp]) => (
              <span key={shipId} className="text-yellow-400">⭐ +{xp} XP (vaisseau principal)</span>
            ))}
          </div>
        )}

        {/* Modules trouvés */}
        {hasMod && (
          <div>
            <p className="text-[10px] text-gray-600 font-display mb-1">MODULE TROUVÉ</p>
            {result.modules_found.map((mod, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-purple-400">🔧</span>
                <span className="text-white">{mod.type} — Niveau {mod.level}</span>
              </div>
            ))}
          </div>
        )}

        {/* Cicatrices */}
        {hasScar && (
          <div>
            <p className="text-[10px] text-gray-600 font-display mb-1">CICATRICE GAGNÉE</p>
            {result.scars_earned.map((scar, i) => (
              <p key={i} className="text-xs text-purple-300 italic">🩹 "{scar.tag}"</p>
            ))}
          </div>
        )}

        {/* Perte deutérium */}
        {result.deuterium_lost && (
          <p className="text-xs text-red-400">⚗️ -{result.deuterium_lost} deutérium (incident de navigation)</p>
        )}
      </div>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────
export function ExpeditionPage() {
  const qc = useQueryClient()
  const [duration, setDuration] = useState<'SHORT' | 'MEDIUM' | 'LONG'>('MEDIUM')
  const [selectedShips, setSelectedShips] = useState<string[]>([])

  const { data: activeExpeditions, isLoading: loadingExp } = useQuery({
    queryKey: ['expeditions', 'active'],
    queryFn: () => api.get<Expedition[]>('/expeditions/active'),
    refetchInterval: 10_000,
  })

  const { data: ships } = useQuery({
    queryKey: ['ships'],
    queryFn: shipsApi.list,
  })

  const availableShips = ships?.filter(s => s.status === 'DOCKED') ?? []

  const { mutate: launch, isPending } = useMutation({
    mutationFn: () => api.post<Expedition>('/expeditions/launch', {
      ship_ids: selectedShips,
      duration,
    }),
    onSuccess: (res) => {
      toast.success(`🚀 Expédition lancée — retour dans ${DURATION_CONFIG[res.duration as keyof typeof DURATION_CONFIG].label} !`, { duration: 5000 })
      qc.invalidateQueries({ queryKey: ['expeditions'] })
      qc.invalidateQueries({ queryKey: ['ships'] })
      setSelectedShips([])
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  function toggleShip(id: string) {
    setSelectedShips(prev => prev.includes(id) ? prev.filter(x => x !== id) : prev.length >= 5 ? prev : [...prev, id])
  }

  const durCfg = DURATION_CONFIG[duration]

  return (
    <div className="space-y-6 animate-fade-in pb-20 lg:pb-0">
      <div>
        <p className="section-title mb-1">Exploration Autonome</p>
        <h1 className="text-2xl font-bold text-white">Centre d'Expédition</h1>
        <p className="text-sm text-gray-500 mt-1">Envoyez vos vaisseaux dans des aventures narratives — XP, ressources, modules rares et cicatrices légendaires.</p>
      </div>

      {/* Expéditions actives */}
      {activeExpeditions && activeExpeditions.length > 0 && (
        <div>
          <p className="section-title mb-3">En cours</p>
          <div className="space-y-4">
            {activeExpeditions.map(exp => {
              const dcfg = DURATION_CONFIG[exp.duration]
              return (
                <div key={exp.expedition_id} className="rounded-2xl overflow-hidden"
                  style={{ background: 'linear-gradient(135deg, rgba(13,18,30,0.95), rgba(8,12,24,0.98))', border: `1px solid rgba(${exp.duration === 'LONG' ? '124,58,237' : exp.duration === 'MEDIUM' ? '45,125,210' : '16,185,129'},0.25)` }}>
                  <div className="h-px" style={{ background: `linear-gradient(90deg, transparent, ${dcfg.color}80, transparent)` }} />
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="text-2xl">{dcfg.icon}</span>
                        <div>
                          <p className="font-semibold text-white">{dcfg.label} — {exp.ship_ids.length} vaisseau{exp.ship_ids.length > 1 ? 'x' : ''}</p>
                          <p className="text-[10px] font-display" style={{ color: dcfg.color }}>RISQUE {dcfg.risk.toUpperCase()}</p>
                        </div>
                      </div>
                      {!exp.is_complete
                        ? <ExpCountdown eta={exp.eta_seconds} onComplete={() => qc.invalidateQueries({ queryKey: ['expeditions'] })} />
                        : <span className="text-green-400 font-display font-bold text-lg">RETOUR !</span>
                      }
                    </div>

                    {!exp.is_complete && (
                      <div className="h-1.5 bg-gray-800/60 rounded-full overflow-hidden">
                        <div className="h-full rounded-full forge-active"
                          style={{ background: `linear-gradient(90deg, ${dcfg.color}60, ${dcfg.color})`, width: '100%' }} />
                      </div>
                    )}

                    {exp.result && <ExpeditionReport result={exp.result} />}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Lancer une expédition */}
      <div className="rounded-2xl overflow-hidden"
        style={{ background: 'rgba(8,12,24,0.95)', border: '1px solid rgba(45,125,210,0.2)' }}>
        <div className="h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(45,125,210,0.6), transparent)' }} />
        <div className="p-5 space-y-5">
          <p className="font-semibold text-white">🚀 Nouvelle expédition</p>

          {/* Durée */}
          <div>
            <p className="section-title mb-2">Durée & Distance</p>
            <div className="grid grid-cols-3 gap-2">
              {(Object.entries(DURATION_CONFIG) as [string, typeof DURATION_CONFIG['SHORT']][]).map(([key, cfg]) => (
                <button key={key} onClick={() => setDuration(key as any)}
                  className="p-3 rounded-xl border text-left transition-all"
                  style={duration === key ? {
                    background: `rgba(${key==='LONG'?'124,58,237':key==='MEDIUM'?'45,125,210':'16,185,129'},0.12)`,
                    border: `1px solid ${cfg.color}50`,
                    boxShadow: `0 0 12px ${cfg.color}20`,
                  } : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)' }}>
                  <p className="text-lg mb-1">{cfg.icon}</p>
                  <p className="text-xs font-semibold text-white">{cfg.label}</p>
                  <p className="text-[10px] mt-0.5" style={{ color: cfg.color }}>⚗️ -{cfg.deuterium}</p>
                  <p className="text-[10px] text-gray-600 mt-1">{cfg.risk}</p>
                </button>
              ))}
            </div>
            <div className="mt-2 text-xs text-gray-500 flex items-start gap-2">
              <span>{durCfg.icon}</span>
              <span>{durCfg.desc}</span>
            </div>
          </div>

          {/* Sélection vaisseaux */}
          <div>
            <p className="section-title mb-2">
              Vaisseaux ({selectedShips.length}/5 sélectionnés)
            </p>
            {availableShips.length === 0 ? (
              <p className="text-xs text-gray-500 italic">Aucun vaisseau amarré disponible</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                {availableShips.map(ship => {
                  const sel = selectedShips.includes(ship.id)
                  const rarity = ship.rarity as Rarity
                  const rc = RARITY_CONFIG[rarity]?.color ?? '#6b7280'
                  return (
                    <button key={ship.id} onClick={() => toggleShip(ship.id)}
                      className="p-2.5 rounded-lg border text-left transition-all"
                      style={sel ? { background: `rgba(${parseInt(rc.slice(1,3),16)},${parseInt(rc.slice(3,5),16)},${parseInt(rc.slice(5,7),16)},0.12)`, border: `1px solid ${rc}50` }
                               : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)' }}>
                      <p className="text-xs font-medium text-white truncate">{ship.ship_type.replace('_', ' ')}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[10px]" style={{ color: rc }}>{rc ? RARITY_CONFIG[rarity]?.label : ship.rarity}</span>
                        <span className="text-[10px] text-gray-600">G{ship.grade}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Lancer */}
          <button
            className="btn-primary w-full py-3"
            disabled={selectedShips.length === 0 || isPending}
            onClick={() => launch()}>
            {isPending ? '⏳ Lancement...' : `🚀 Envoyer ${selectedShips.length} vaisseau${selectedShips.length > 1 ? 'x' : ''} (${durCfg.label})`}
          </button>

          {/* Tableau des événements possibles */}
          <details className="cursor-pointer">
            <summary className="text-[10px] text-gray-600 font-display tracking-wider hover:text-gray-400 transition-colors">
              ▼ VOIR LES ÉVÉNEMENTS POSSIBLES
            </summary>
            <div className="mt-3 grid grid-cols-2 gap-1.5">
              {[
                { icon: '🪐', label: 'Champ de débris', chance: '18%', type: 'good' },
                { icon: '👾', label: 'Artefact alien',   chance: '12%', type: 'good' },
                { icon: '🛸', label: 'Station abandonnée',chance:'10%', type: 'good' },
                { icon: '📦', label: 'Cargo pirate',     chance: '5%',  type: 'good' },
                { icon: '🌀', label: 'Tempête du vide',  chance: '15%', type: 'neutral' },
                { icon: '📡', label: 'Signal mystérieux', chance: '10%', type: 'neutral' },
                { icon: '🧭', label: 'Erreur navigation', chance: '5%',  type: 'neutral' },
                { icon: '⚔️', label: 'Embuscade pirate', chance: '10%', type: 'bad' },
                { icon: '☢️', label: 'Zone radiation',   chance: '6%',  type: 'bad' },
                { icon: '🚨', label: 'Patrouille ennemie',chance:'4%',  type: 'bad' },
                { icon: '💎', label: 'Épave légendaire', chance: '3%',  type: 'epic' },
                { icon: '🌌', label: 'Premier contact',  chance: '2%',  type: 'epic' },
              ].map(ev => (
                <div key={ev.label} className="flex items-center gap-2 text-xs p-1.5 rounded-lg"
                  style={{ background: ev.type === 'good' ? 'rgba(16,185,129,0.05)' : ev.type === 'bad' ? 'rgba(239,68,68,0.05)' : ev.type === 'epic' ? 'rgba(124,58,237,0.08)' : 'rgba(20,28,42,0.4)' }}>
                  <span>{ev.icon}</span>
                  <span className="text-gray-400 truncate flex-1">{ev.label}</span>
                  <span className={`text-[10px] shrink-0 ${ev.type === 'good' ? 'text-green-500' : ev.type === 'bad' ? 'text-red-500' : ev.type === 'epic' ? 'text-purple-400' : 'text-gray-600'}`}>
                    {ev.chance}
                  </span>
                </div>
              ))}
            </div>
          </details>
        </div>
      </div>
    </div>
  )
}
