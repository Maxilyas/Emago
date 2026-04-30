import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { fmt, fmtCountdown } from '@/lib/utils'
import { LoadingSpinner } from '@/components/ui'

// ─── Types ────────────────────────────────────────────────────────────────────
interface TechNode {
  label: string; desc: string; icon: string
  max_level: number; current_level: number
  max_reached: boolean; prereqs_met: boolean
  is_researching: boolean
  requires: Array<{ tech_id: string; level: number }>
  costs: Array<{ metal: number; crystal: number; deuterium: number; hours: number }>
  per_level_bonus: Record<string, number>
  bonus_summary: Record<string, number>
  next_cost: { metal: number; crystal: number; deuterium: number; hours: number } | null
}

interface TechTree {
  by_class: Record<string, Record<string, TechNode>>
  active_research: {
    tech_id: string; tech_label: string; target_level: number
    started_at: string; completes_at: string; eta_seconds: number
  } | null
}

// ─── Config visuelle par classe ────────────────────────────────────────────────
const CLASS_CONFIG = {
  ATTACK:      { label: 'Attaque',      color: '#ef4444', icon: '⚔️', bg: 'rgba(239,68,68,0.06)' },
  DEFENSE:     { label: 'Défense',      color: '#3b82f6', icon: '🛡️', bg: 'rgba(59,130,246,0.06)' },
  SUPPORT:     { label: 'Soutien',      color: '#22c55e', icon: '💊', bg: 'rgba(34,197,94,0.06)' },
  EXPLORATION: { label: 'Exploration',  color: '#a855f7', icon: '🔭', bg: 'rgba(168,85,247,0.06)' },
}

const BONUS_LABELS: Record<string, string> = {
  dps: 'DPS', hull: 'Coque', shield: 'Bouclier', speed: 'Vitesse',
  stealth: 'Furtivité', cargo: 'Cargo', support_aura: 'Aura',
  shield_regen: 'Régén. bouclier', repair_rate: 'Réparation',
  rng_floor: 'Plancher RNG', expedition_bonus: 'Bonus expédition',
}

function hexToRgb(hex: string) {
  try { return `${parseInt(hex.slice(1,3),16)},${parseInt(hex.slice(3,5),16)},${parseInt(hex.slice(5,7),16)}` }
  catch { return '107,114,128' }
}

// ─── Noeud technologique ──────────────────────────────────────────────────────
function TechCard({ techId, tech, classColor, onResearch, isResearching }: {
  techId: string; tech: TechNode; classColor: string
  onResearch: (id: string) => void; isResearching: boolean
}) {
  const canResearch = tech.prereqs_met && !tech.max_reached && !tech.is_researching && !isResearching
  const rgb = hexToRgb(classColor)

  return (
    <div className="rounded-xl border transition-all duration-200 overflow-hidden"
      style={{
        borderColor: tech.max_reached ? `rgba(${rgb},0.4)` : tech.prereqs_met ? `rgba(${rgb},0.2)` : 'rgba(35,50,70,0.4)',
        background: tech.max_reached ? `rgba(${rgb},0.06)` : tech.prereqs_met ? `rgba(13,18,30,0.9)` : 'rgba(8,12,24,0.8)',
        opacity: !tech.prereqs_met ? 0.6 : 1,
      }}>

      {/* Barre de progression niveaux */}
      {tech.max_reached && (
        <div className="h-0.5" style={{ background: `linear-gradient(90deg, transparent, ${classColor}, transparent)` }} />
      )}

      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="h-10 w-10 rounded-xl flex items-center justify-center text-xl shrink-0"
            style={{ background: `rgba(${rgb},0.1)`, border: `1px solid rgba(${rgb},0.2)` }}>
            {tech.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-sm text-white">{tech.label}</p>
              {tech.max_reached ? (
                <span className="text-[10px] font-display px-2 py-0.5 rounded-full"
                  style={{ color: classColor, background: `rgba(${rgb},0.15)`, border: `1px solid rgba(${rgb},0.3)` }}>
                  MAX
                </span>
              ) : (
                <span className="text-[10px] font-display" style={{ color: classColor }}>
                  {tech.current_level}/{tech.max_level}
                </span>
              )}
            </div>
            <p className="text-[10px] text-gray-500 mt-0.5 leading-relaxed">{tech.desc}</p>
          </div>
        </div>

        {/* Barre niveaux */}
        <div className="flex gap-1 mb-3">
          {Array.from({ length: tech.max_level }).map((_, i) => (
            <div key={i} className="flex-1 h-1.5 rounded-full"
              style={{ background: i < tech.current_level ? classColor : 'rgba(35,50,70,0.6)' }} />
          ))}
        </div>

        {/* Bonus actuels */}
        {tech.current_level > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {Object.entries(tech.bonus_summary).map(([stat, val]) => (
              <span key={stat} className="text-[10px] px-2 py-0.5 rounded-full"
                style={{ background: `rgba(${rgb},0.1)`, border: `1px solid rgba(${rgb},0.2)`, color: classColor }}>
                +{typeof val === 'number' && val < 1 ? `${Math.round(val * 100)}%` : val} {BONUS_LABELS[stat] ?? stat}
              </span>
            ))}
          </div>
        )}

        {/* Prérequis non remplis */}
        {!tech.prereqs_met && tech.requires.length > 0 && (
          <p className="text-[10px] text-red-400 mb-2">
            🔒 Prérequis : {tech.requires.map(r => `${r.tech_id.split('_').slice(1).join(' ')} Niv.${r.level}`).join(', ')}
          </p>
        )}

        {/* Recherche en cours */}
        {tech.is_researching && (
          <div className="text-xs text-accent-blue font-display animate-pulse">⚗️ RECHERCHE EN COURS...</div>
        )}

        {/* Prochain niveau + coût */}
        {!tech.max_reached && !tech.is_researching && tech.prereqs_met && tech.next_cost && (
          <>
            <div className="flex flex-wrap gap-2 mb-2 text-xs">
              {tech.next_cost.metal > 0 && <span className="text-gray-400">⛏️ {fmt(tech.next_cost.metal)}</span>}
              {tech.next_cost.crystal > 0 && <span className="text-gray-400">💎 {fmt(tech.next_cost.crystal)}</span>}
              {tech.next_cost.deuterium > 0 && <span className="text-gray-400">⚗️ {fmt(tech.next_cost.deuterium)}</span>}
              <span className="text-gray-600">⏱ {fmtCountdown(tech.next_cost.hours * 3600)}</span>
            </div>
            <button
              onClick={() => onResearch(techId)}
              disabled={!canResearch}
              className="w-full py-1.5 rounded-lg text-xs font-display tracking-wider transition-all"
              style={canResearch ? {
                background: `rgba(${rgb},0.15)`, border: `1px solid rgba(${rgb},0.35)`, color: classColor,
              } : {
                background: 'rgba(30,40,55,0.4)', border: '1px solid rgba(45,58,80,0.4)', color: '#374151',
              }}>
              {isResearching ? 'RECHERCHE EN COURS' : `RECHERCHER → Niv.${tech.current_level + 1}`}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────
export function TechPage() {
  const qc = useQueryClient()
  const [activeClass, setActiveClass] = useState<keyof typeof CLASS_CONFIG>('ATTACK')

  const { data: tree, isLoading } = useQuery({
    queryKey: ['tech', 'tree'],
    queryFn: () => api.get<TechTree>('/tech/tree'),
    refetchInterval: 30_000,
  })

  const { mutate: research } = useMutation({
    mutationFn: (techId: string) => api.post('/tech/research', { tech_id: techId }),
    onSuccess: (_, techId) => {
      toast.success(`🔬 Recherche lancée !`, { duration: 4000 })
      qc.invalidateQueries({ queryKey: ['tech'] })
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  const activeResearch = tree?.active_research
  const classTechs = tree?.by_class[activeClass] ?? {}
  const cfg = CLASS_CONFIG[activeClass]

  return (
    <div className="space-y-5 animate-fade-in pb-20 lg:pb-0">
      <div>
        <p className="section-title mb-1">Salle de Recherche</p>
        <h1 className="text-2xl font-bold text-white">Arbre Technologique</h1>
        <p className="text-sm text-gray-500 mt-1">Des bonus permanents par classe. Chaque niveau améliore tous vos vaisseaux de cette classe.</p>
      </div>

      {/* Recherche active */}
      {activeResearch && (
        <div className="panel" style={{ borderColor: 'rgba(124,58,237,0.3)', background: 'rgba(124,58,237,0.05)' }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg flex items-center justify-center"
                style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)' }}>
                🔬
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{activeResearch.tech_label}</p>
                <p className="text-xs text-purple-400">→ Niveau {activeResearch.target_level}</p>
              </div>
            </div>
            <ResearchCountdown eta={activeResearch.eta_seconds} onDone={() => {
              toast.success('🎉 Recherche terminée ! Réclamez le bonus.')
              qc.invalidateQueries({ queryKey: ['tech'] })
            }} />
          </div>
        </div>
      )}

      {/* Sélecteur de classe */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {(Object.entries(CLASS_CONFIG) as [keyof typeof CLASS_CONFIG, typeof CLASS_CONFIG['ATTACK']][]).map(([cls, clsCfg]) => {
          const techs = Object.values(tree?.by_class[cls] ?? {})
          const done  = techs.filter(t => t.max_reached).length
          const total = techs.length
          return (
            <button key={cls} onClick={() => setActiveClass(cls)}
              className="p-3 rounded-xl border text-left transition-all"
              style={activeClass === cls ? {
                background: `rgba(${hexToRgb(clsCfg.color)},0.12)`,
                border: `1px solid rgba(${hexToRgb(clsCfg.color)},0.4)`,
                boxShadow: `0 0 12px rgba(${hexToRgb(clsCfg.color)},0.2)`,
              } : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)' }}>
              <p className="text-xl mb-1">{clsCfg.icon}</p>
              <p className="text-xs font-semibold text-white">{clsCfg.label}</p>
              <p className="text-[10px] mt-1" style={{ color: activeClass === cls ? clsCfg.color : '#6b7280' }}>
                {done}/{total} maîtrisées
              </p>
            </button>
          )
        })}
      </div>

      {/* Arbres de la classe sélectionnée */}
      {isLoading ? (
        <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>
      ) : (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">{cfg.icon}</span>
            <div>
              <p className="font-semibold text-white">{cfg.label}</p>
              <p className="text-xs text-gray-500">Bonus appliqués à tous vos vaisseaux {cfg.label.toLowerCase()}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(classTechs).map(([id, tech]) => (
              <TechCard
                key={id} techId={id} tech={tech} classColor={cfg.color}
                onResearch={research}
                isResearching={!!activeResearch && activeResearch.tech_id !== id}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ResearchCountdown({ eta: initEta, onDone }: { eta: number; onDone: () => void }) {
  const [s, setS] = useState(initEta)
  React.useEffect(() => {
    if (initEta <= 0) { onDone(); return }
    const start = Date.now()
    const id = setInterval(() => {
      const left = Math.max(0, initEta - (Date.now() - start) / 1000)
      setS(Math.round(left)); if (left <= 0) { clearInterval(id); onDone() }
    }, 1000)
    return () => clearInterval(id)
  }, [initEta])
  if (s <= 0) return <button className="btn-primary text-xs py-1.5">Réclamer !</button>
  return <span className="font-mono text-purple-400 text-sm">{fmtCountdown(s)}</span>
}
