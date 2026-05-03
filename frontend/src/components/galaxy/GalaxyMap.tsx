import React, { useState, useCallback } from 'react'
import type { FC } from 'react'
import type { GhostShipOut } from '@/types'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SystemPlanet {
  position: number
  planet_id: string | null
  name: string | null
  owner_id: string | null
  owner_username: string | null
  is_own: boolean
}

interface Props {
  planets: SystemPlanet[]
  ghostShips?: GhostShipOut[]
  currentPlayerId: string
  onSelectPlanet?: (planet: SystemPlanet) => void
  onSelectGhost?: (ghost: GhostShipOut) => void
  selectedPlanetId?: string | null
  selectedGhostId?: string | null
}

// ─── Layout SVG ──────────────────────────────────────────────────────────────

const SVG_SIZE = 500
const CENTER = SVG_SIZE / 2

const ORBITS = [
  { radius: 55,  positions: [1, 2, 3]    },
  { radius: 105, positions: [4, 5, 6]    },
  { radius: 155, positions: [7, 8, 9]    },
  { radius: 205, positions: [10, 11, 12] },
  { radius: 235, positions: [13, 14, 15] },
]
const ORBIT_OFFSETS = [0, 40, 70, 20, 55]

function getPlanetPosition(orbitIndex: number, positionInOrbit: number) {
  const orbit = ORBITS[orbitIndex]
  const count = orbit.positions.length
  const angleDeg = ORBIT_OFFSETS[orbitIndex] + (positionInOrbit / count) * 360
  const angleRad = (angleDeg * Math.PI) / 180
  return {
    x: CENTER + orbit.radius * Math.cos(angleRad),
    y: CENTER + orbit.radius * Math.sin(angleRad),
  }
}

// Position stable d'un ghost ship dérivée de son ID (hash simple)
function getGhostPosition(ghostId: string, index: number): { x: number; y: number } {
  let hash = 0
  for (let i = 0; i < ghostId.length; i++) hash = (hash * 31 + ghostId.charCodeAt(i)) & 0xffffffff
  const orbitRadii = [80, 130, 180, 220]
  const orbitIdx = Math.abs(hash + index * 7) % orbitRadii.length
  const angle = ((Math.abs(hash * 13 + index * 97) % 360) * Math.PI) / 180
  const r = orbitRadii[orbitIdx]
  return { x: CENTER + r * Math.cos(angle), y: CENTER + r * Math.sin(angle) }
}

const RARITY_COLOR: Record<string, string> = {
  COMMON:    '#9ca3af',
  RARE:      '#818cf8',
  LEGENDARY: '#fbbf24',
}

function getPlanetColor(planet: SystemPlanet): string {
  if (!planet.planet_id) return '#374151'
  if (planet.is_own) return '#2196F3'
  return '#E53935'
}
function getPlanetRadius(planet: SystemPlanet): number {
  if (!planet.planet_id) return 5
  if (planet.is_own) return 8
  return 7
}

// ─── Composant ───────────────────────────────────────────────────────────────

export const GalaxyMap: FC<Props> = ({
  planets, ghostShips = [], onSelectPlanet, onSelectGhost,
  selectedPlanetId, selectedGhostId,
}) => {
  const [hoveredPos, setHoveredPos] = useState<number | null>(null)
  const [hoveredGhost, setHoveredGhost] = useState<string | null>(null)

  const planetByPos = React.useMemo(() => {
    const map: Record<number, SystemPlanet> = {}
    for (const p of planets) map[p.position] = p
    return map
  }, [planets])

  const handlePlanetClick = useCallback((planet: SystemPlanet) => {
    if (planet.planet_id && onSelectPlanet) onSelectPlanet(planet)
  }, [onSelectPlanet])

  const handleGhostClick = useCallback((ghost: GhostShipOut) => {
    if (!ghost.is_defeated && onSelectGhost) onSelectGhost(ghost)
  }, [onSelectGhost])

  const stars = React.useMemo(() =>
    Array.from({ length: 60 }, (_, i) => ({
      cx: (Math.sin(i * 13.7) * 0.5 + 0.5) * SVG_SIZE,
      cy: (Math.sin(i * 7.3) * 0.5 + 0.5) * SVG_SIZE,
      r: (Math.sin(i * 3.1) * 0.5 + 0.5) * 1.5 + 0.5,
      opacity: (Math.sin(i * 5.7) * 0.5 + 0.5) * 0.6 + 0.2,
    })), []
  )

  const activeGhosts = ghostShips.filter(g => !g.is_defeated)
  const defeatedGhosts = ghostShips.filter(g => g.is_defeated)

  return (
    <div className="relative w-full max-w-lg mx-auto">
      <svg
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        className="w-full h-auto rounded-xl bg-gray-900 border border-gray-700"
        style={{ maxHeight: 480 }}
      >
        {/* Étoiles fond */}
        <g opacity="0.7">
          {stars.map((s, i) => (
            <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill="white" opacity={s.opacity} />
          ))}
        </g>

        {/* Soleil */}
        <circle cx={CENTER} cy={CENTER} r={18} fill="#FFB300" opacity={0.9} />
        <circle cx={CENTER} cy={CENTER} r={22} fill="#FFB300" opacity={0.2} />
        <circle cx={CENTER} cy={CENTER} r={28} fill="#FFB300" opacity={0.08} />

        {/* Orbites */}
        {ORBITS.map((orbit, i) => (
          <circle key={i} cx={CENTER} cy={CENTER} r={orbit.radius}
            fill="none" stroke="#374151" strokeWidth="0.5" strokeDasharray="3 5" />
        ))}

        {/* Ghost ships vaincus (fantômes grisés) */}
        {defeatedGhosts.map((ghost, idx) => {
          const { x, y } = getGhostPosition(ghost.id, idx)
          const eta = ghost.respawn_at ? new Date(ghost.respawn_at) : null
          const minsLeft = eta ? Math.max(0, Math.ceil((eta.getTime() - Date.now()) / 60000)) : 0
          return (
            <g key={ghost.id} opacity={0.3}>
              <text x={x} y={y + 5} textAnchor="middle" fontSize="14" fill="#4b5563">👻</text>
              <text x={x} y={y + 18} textAnchor="middle" fontSize="7" fill="#4b5563">
                {minsLeft}min
              </text>
            </g>
          )
        })}

        {/* Ghost ships actifs */}
        {activeGhosts.map((ghost, idx) => {
          const { x, y } = getGhostPosition(ghost.id, idx)
          const color = RARITY_COLOR[ghost.rarity] ?? '#9ca3af'
          const isSelected = ghost.id === selectedGhostId
          const isHovered = hoveredGhost === ghost.id
          const hpPct = ghost.max_hull > 0 ? ghost.current_hull / ghost.max_hull : 1

          return (
            <g key={ghost.id}
              onClick={() => handleGhostClick(ghost)}
              onMouseEnter={() => setHoveredGhost(ghost.id)}
              onMouseLeave={() => setHoveredGhost(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Halo de sélection */}
              {isSelected && (
                <circle cx={x} cy={y} r={16} fill="none" stroke={color} strokeWidth="1.5" opacity={0.8}
                  strokeDasharray="3 2" />
              )}
              {/* Halo hover */}
              {isHovered && !isSelected && (
                <circle cx={x} cy={y} r={14} fill={color} opacity={0.12} />
              )}
              {/* Icône fantôme */}
              <text x={x} y={y + 5} textAnchor="middle" fontSize="16"
                style={{ filter: `drop-shadow(0 0 4px ${color})` }}>
                👻
              </text>
              {/* Barre de vie */}
              <rect x={x - 10} y={y + 9} width={20} height={2.5} rx={1} fill="#1f2937" />
              <rect x={x - 10} y={y + 9} width={20 * hpPct} height={2.5} rx={1}
                fill={hpPct > 0.5 ? '#22c55e' : hpPct > 0.25 ? '#f59e0b' : '#ef4444'} />
              {/* Tooltip hover */}
              {isHovered && (
                <g>
                  <rect x={x - 45} y={y - 44} width={90} height={36} rx={4}
                    fill="#111827" stroke={color} strokeWidth="0.5" opacity={0.95} />
                  <text x={x} y={y - 30} textAnchor="middle" fontSize="8.5"
                    fill={color} fontWeight="bold">
                    {ghost.name.length > 16 ? ghost.name.slice(0, 15) + '…' : ghost.name}
                  </text>
                  <text x={x} y={y - 19} textAnchor="middle" fontSize="7.5" fill="#9ca3af">
                    {'⚠️'.repeat(ghost.threat_level)} Niv.{ghost.threat_level} — {ghost.rarity}
                  </text>
                  <text x={x} y={y - 10} textAnchor="middle" fontSize="7" fill="#6b7280">
                    {ghost.current_hull}/{ghost.max_hull} PV · Cliquez pour attaquer
                  </text>
                </g>
              )}
            </g>
          )
        })}

        {/* Planètes */}
        {ORBITS.map((orbit, orbitIdx) =>
          orbit.positions.map((pos, posIdx) => {
            const planet = planetByPos[pos]
            if (!planet) return null
            const { x, y } = getPlanetPosition(orbitIdx, posIdx)
            const color = getPlanetColor(planet)
            const radius = getPlanetRadius(planet)
            const isSelected = planet.planet_id === selectedPlanetId
            const isHovered = hoveredPos === pos

            return (
              <g key={pos}
                onClick={() => handlePlanetClick(planet)}
                onMouseEnter={() => setHoveredPos(pos)}
                onMouseLeave={() => setHoveredPos(null)}
                style={{ cursor: planet.planet_id ? 'pointer' : 'default' }}
              >
                {isSelected && (
                  <circle cx={x} cy={y} r={radius + 6} fill="none" stroke="#2196F3"
                    strokeWidth="1.5" opacity={0.8} />
                )}
                {isHovered && !isSelected && (
                  <circle cx={x} cy={y} r={radius + 4} fill={color} opacity={0.15} />
                )}
                <circle cx={x} cy={y} r={radius} fill={color}
                  opacity={planet.planet_id ? 0.9 : 0.4}
                  stroke={isSelected ? '#2196F3' : 'transparent'}
                  strokeWidth={isSelected ? 1.5 : 0}
                />
                <text x={x} y={y + radius + 10} textAnchor="middle" fontSize="8" fill="#6B7280">
                  {pos}
                </text>
                {isHovered && planet.owner_username && (
                  <g>
                    <rect x={x - 35} y={y - radius - 28} width={70} height={20} rx={4}
                      fill="#1F2937" stroke="#374151" />
                    <text x={x} y={y - radius - 14} textAnchor="middle" fontSize="9"
                      fill={planet.is_own ? '#2196F3' : '#E53935'}>
                      {planet.owner_username.slice(0, 10)}
                    </text>
                  </g>
                )}
              </g>
            )
          })
        )}
      </svg>

      {/* Légende */}
      <div className="flex gap-4 justify-center mt-3 text-xs text-gray-400 flex-wrap">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" /> Ma planète
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" /> Autre joueur
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-gray-600 inline-block" /> Vide
        </span>
        <span className="flex items-center gap-1.5">
          <span className="text-sm">👻</span> Vaisseau fantôme
        </span>
      </div>
    </div>
  )
}
