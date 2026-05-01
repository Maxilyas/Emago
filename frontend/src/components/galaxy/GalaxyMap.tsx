/**
 * components/galaxy/GalaxyMap.tsx
 * Agent 6 — Développeur Frontend | Sprint 3
 * Design : Agent 4 — UI/UX
 *
 * Composant cartographique interactif du système solaire.
 * Remplace la grille textuelle de GalaxyPage.tsx.
 *
 * Affiche :
 *   - Les 15 positions d'un système sur des orbites concentriques
 *   - Les planètes occupées (colorées selon propriétaire)
 *   - Les positions vides (grises)
 *   - La sélection d'une planète cible pour envoyer une flotte
 *
 * Design : Dark UI, ambiance spatiale, étoiles en background SVG
 */
import React, { useState, useCallback } from 'react'
import type { FC } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SystemPlanet {
  position: number        // 1-15
  planet_id: string | null
  name: string | null
  owner_id: string | null
  owner_username: string | null
  is_own: boolean
}

interface Props {
  planets: SystemPlanet[]
  currentPlayerId: string
  onSelectPlanet?: (planet: SystemPlanet) => void
  selectedPlanetId?: string | null
}

// ─── Constantes layout SVG ────────────────────────────────────────────────────

const SVG_SIZE = 500
const CENTER = SVG_SIZE / 2

// 5 orbites, 3 planètes chacune (positions 1-15)
const ORBITS = [
  { radius: 55,  positions: [1, 2, 3]      },
  { radius: 105, positions: [4, 5, 6]      },
  { radius: 155, positions: [7, 8, 9]      },
  { radius: 205, positions: [10, 11, 12]   },
  { radius: 235, positions: [13, 14, 15]   },
]

// Angles de départ par orbite (déphasage pour éviter l'alignement)
const ORBIT_OFFSETS = [0, 40, 70, 20, 55]

function getPlanetPosition(orbitIndex: number, positionInOrbit: number): { x: number; y: number } {
  const orbit = ORBITS[orbitIndex]
  const count = orbit.positions.length
  const angleDeg = ORBIT_OFFSETS[orbitIndex] + (positionInOrbit / count) * 360
  const angleRad = (angleDeg * Math.PI) / 180
  return {
    x: CENTER + orbit.radius * Math.cos(angleRad),
    y: CENTER + orbit.radius * Math.sin(angleRad),
  }
}

function getPlanetColor(planet: SystemPlanet): string {
  if (!planet.planet_id) return '#374151'       // vide — gris foncé
  if (planet.is_own) return '#2196F3'           // propre planète — bleu
  return '#E53935'                               // autre joueur — rouge
}

function getPlanetRadius(planet: SystemPlanet): number {
  if (!planet.planet_id) return 5
  if (planet.is_own) return 8
  return 7
}

// ─── Composant ───────────────────────────────────────────────────────────────

export const GalaxyMap: FC<Props> = ({ planets, onSelectPlanet, selectedPlanetId }) => {
  const [hovered, setHovered] = useState<number | null>(null)

  // Indexer les planètes par position
  const planetByPos = React.useMemo(() => {
    const map: Record<number, SystemPlanet> = {}
    for (const p of planets) map[p.position] = p
    return map
  }, [planets])

  const handleClick = useCallback((planet: SystemPlanet) => {
    if (planet.planet_id && onSelectPlanet) {
      onSelectPlanet(planet)
    }
  }, [onSelectPlanet])

  // Étoiles de fond (fixes, générées depuis l'index)
  const stars = React.useMemo(() =>
    Array.from({ length: 60 }, (_, i) => ({
      cx: (Math.sin(i * 13.7) * 0.5 + 0.5) * SVG_SIZE,
      cy: (Math.sin(i * 7.3) * 0.5 + 0.5) * SVG_SIZE,
      r: (Math.sin(i * 3.1) * 0.5 + 0.5) * 1.5 + 0.5,
      opacity: (Math.sin(i * 5.7) * 0.5 + 0.5) * 0.6 + 0.2,
    })), []
  )

  return (
    <div className="relative w-full max-w-lg mx-auto">
      <svg
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        className="w-full h-auto rounded-xl bg-gray-900 border border-gray-700"
        style={{ maxHeight: 480 }}
      >
        {/* Étoiles de fond */}
        <g opacity="0.7">
          {stars.map((s, i) => (
            <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill="white" opacity={s.opacity} />
          ))}
        </g>

        {/* Étoile centrale */}
        <circle cx={CENTER} cy={CENTER} r={18} fill="#FFB300" opacity={0.9} />
        <circle cx={CENTER} cy={CENTER} r={22} fill="#FFB300" opacity={0.2} />
        <circle cx={CENTER} cy={CENTER} r={28} fill="#FFB300" opacity={0.08} />

        {/* Orbites */}
        {ORBITS.map((orbit, i) => (
          <circle
            key={i}
            cx={CENTER}
            cy={CENTER}
            r={orbit.radius}
            fill="none"
            stroke="#374151"
            strokeWidth="0.5"
            strokeDasharray="3 5"
          />
        ))}

        {/* Planètes */}
        {ORBITS.map((orbit, orbitIdx) =>
          orbit.positions.map((pos, posIdx) => {
            const planet = planetByPos[pos]
            if (!planet) return null

            const { x, y } = getPlanetPosition(orbitIdx, posIdx)
            const color = getPlanetColor(planet)
            const radius = getPlanetRadius(planet)
            const isSelected = planet.planet_id === selectedPlanetId
            const isHovered = hovered === pos

            return (
              <g
                key={pos}
                onClick={() => handleClick(planet)}
                onMouseEnter={() => setHovered(pos)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: planet.planet_id ? 'pointer' : 'default' }}
              >
                {/* Halo de sélection */}
                {isSelected && (
                  <circle cx={x} cy={y} r={radius + 6} fill="none" stroke="#2196F3" strokeWidth="1.5" opacity={0.8} />
                )}
                {/* Halo hover */}
                {isHovered && !isSelected && (
                  <circle cx={x} cy={y} r={radius + 4} fill={color} opacity={0.15} />
                )}

                {/* Planète */}
                <circle
                  cx={x}
                  cy={y}
                  r={radius}
                  fill={color}
                  opacity={planet.planet_id ? 0.9 : 0.4}
                  stroke={isSelected ? '#2196F3' : 'transparent'}
                  strokeWidth={isSelected ? 1.5 : 0}
                />

                {/* Label position */}
                <text
                  x={x}
                  y={y + radius + 10}
                  textAnchor="middle"
                  fontSize="8"
                  fill="#6B7280"
                >
                  {pos}
                </text>

                {/* Tooltip (nom du propriétaire) */}
                {isHovered && planet.owner_username && (
                  <g>
                    <rect
                      x={x - 35}
                      y={y - radius - 28}
                      width={70}
                      height={20}
                      rx={4}
                      fill="#1F2937"
                      stroke="#374151"
                    />
                    <text
                      x={x}
                      y={y - radius - 14}
                      textAnchor="middle"
                      fontSize="9"
                      fill={planet.is_own ? '#2196F3' : '#E53935'}
                    >
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
      <div className="flex gap-4 justify-center mt-3 text-xs text-gray-400">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" /> Ma planète
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" /> Autre joueur
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-gray-600 inline-block" /> Vide
        </span>
      </div>
    </div>
  )
}
