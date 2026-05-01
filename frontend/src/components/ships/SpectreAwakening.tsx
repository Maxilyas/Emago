/**
 * components/ships/SpectreAwakening.tsx
 * Agent 6 — Sprint RPG
 *
 * Animation fullscreen déclenchée quand un vaisseau atteint le Grade 5 (Spectre).
 * Montée dans AppLayout — disponible sur toutes les routes.
 *
 * Flux :
 *   WS ship.grade_up (new_grade === 5)
 *     → handleGradeUp dans NotificationPanel appelle setSpectreData(data)
 *     → gameStore.spectreData devient non-null
 *     → AppLayout rend <SpectreAwakening data={spectreData} onDismiss={...} />
 *
 * Phases de l'animation :
 *   flash   (200ms)  — éclair blanc
 *   emerge  (700ms)  — silhouette sort de l'ombre, particules apparaissent
 *   reveal  (700ms)  — titre SPECTRE + nom du vaisseau
 *   hold    (1400ms) — maintien de l'état final
 *   exit    (500ms)  — fondu sortant, puis onDismiss()
 *
 * Aucune dépendance externe — zero import depuis @/types pour éviter les
 * couplages fragiles. Le composant est autonome.
 */
import React, { useEffect, useState } from 'react'

// ─── Types exportés ───────────────────────────────────────────────────────────

export interface SpectreAwakeningData {
  ship_id:    string
  owner_id:   string
  old_grade:  number
  new_grade:  number  // doit être 5
  combat_xp:  number
  ship_name?: string | null   // présent si le vaisseau a un nom (RARE+)
  ship_class?: string         // optionnel — pour future variation de silhouette
}

interface Props {
  data:      SpectreAwakeningData | null
  onDismiss: () => void
}

// ─── Types internes ───────────────────────────────────────────────────────────

type Phase = 'flash' | 'emerge' | 'reveal' | 'hold' | 'exit'

// ─── Particule ────────────────────────────────────────────────────────────────

interface ParticleProps {
  x: number; y: number; size: number; color: string; delay: number
}

function Particle({ x, y, size, color, delay }: ParticleProps) {
  return (
    <div
      style={{
        position:  'absolute',
        left:      `${x}%`,
        top:       `${y}%`,
        width:     size,
        height:    size,
        background: color,
        borderRadius: '50%',
        opacity:   0,
        pointerEvents: 'none',
        animation: `spectre-particle 1.8s ${delay}s ease-out forwards`,
      }}
    />
  )
}

// Positions fixes des particules — déterministes pour éviter le re-render
const PARTICLES: ParticleProps[] = [
  { x: 20, y: 30, size: 4, color: '#FFD700', delay: 0.10 },
  { x: 80, y: 25, size: 3, color: '#9C27B0', delay: 0.20 },
  { x: 15, y: 70, size: 5, color: '#FFD700', delay: 0.00 },
  { x: 85, y: 65, size: 3, color: '#a855f7', delay: 0.30 },
  { x: 50, y: 15, size: 4, color: '#FFD700', delay: 0.15 },
  { x: 45, y: 80, size: 3, color: '#9C27B0', delay: 0.25 },
  { x: 30, y: 50, size: 2, color: '#FFD700', delay: 0.05 },
  { x: 70, y: 45, size: 5, color: '#c084fc', delay: 0.35 },
  { x: 10, y: 45, size: 3, color: '#FFD700', delay: 0.10 },
  { x: 90, y: 40, size: 4, color: '#9C27B0', delay: 0.20 },
  { x: 55, y: 20, size: 2, color: '#FFD700', delay: 0.30 },
  { x: 25, y: 85, size: 4, color: '#a855f7', delay: 0.05 },
]

// ─── Composant principal ──────────────────────────────────────────────────────

export function SpectreAwakening({ data, onDismiss }: Props) {
  const [phase, setPhase] = useState<Phase>('flash')

  useEffect(() => {
    if (!data) return

    setPhase('flash')
    const t1 = setTimeout(() => setPhase('emerge'),  200)
    const t2 = setTimeout(() => setPhase('reveal'),  900)
    const t3 = setTimeout(() => setPhase('hold'),   1600)
    const t4 = setTimeout(() => setPhase('exit'),   4000)
    const t5 = setTimeout(onDismiss,                4500)

    return () => {
      clearTimeout(t1); clearTimeout(t2)
      clearTimeout(t3); clearTimeout(t4); clearTimeout(t5)
    }
  }, [data, onDismiss])

  if (!data) return null

  const showContent  = phase === 'emerge' || phase === 'reveal' || phase === 'hold'
  const showTitle    = phase === 'reveal' || phase === 'hold'
  const isFlash      = phase === 'flash'

  return (
    <>
      {/* ── Keyframes ── */}
      <style>{`
        @keyframes spectre-particle {
          0%   { opacity: 0; transform: translateY(0) scale(0); }
          20%  { opacity: 1; transform: translateY(-20px) scale(1); }
          100% { opacity: 0; transform: translateY(-80px) scale(0.5); }
        }
        @keyframes spectre-emerge {
          0%   { opacity: 0; transform: scale(0.6) translateY(20px); filter: blur(12px); }
          100% { opacity: 1; transform: scale(1)   translateY(0);    filter: blur(0); }
        }
        @keyframes spectre-title {
          0%   { opacity: 0; letter-spacing: 0.6em; }
          100% { opacity: 1; letter-spacing: 0.3em; }
        }
        @keyframes spectre-glow {
          0%, 100% { opacity: 0.35; }
          50%      { opacity: 0.75; }
        }
        @keyframes spectre-exit {
          0%   { opacity: 1; }
          100% { opacity: 0; }
        }
      `}</style>

      {/* ── Overlay fullscreen ── */}
      <div
        onClick={onDismiss}
        style={{
          position:   'fixed',
          inset:       0,
          zIndex:      9999,
          display:    'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor:     'pointer',
          background: isFlash ? 'rgba(255,255,255,0.95)' : 'rgba(5,8,16,0.97)',
          transition: isFlash ? 'none' : 'background 0.4s ease',
          animation:  phase === 'exit' ? 'spectre-exit 0.5s ease forwards' : undefined,
        }}
      >
        {/* Particules */}
        {showContent && PARTICLES.map((p, i) => <Particle key={i} {...p} />)}

        {/* Halo de fond */}
        {!isFlash && (
          <div style={{
            position:   'absolute',
            width:       420,
            height:      420,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(156,39,176,0.18) 0%, transparent 70%)',
            pointerEvents: 'none',
            animation:  'spectre-glow 2s ease-in-out infinite',
          }} />
        )}

        {/* Contenu central */}
        {showContent && (
          <div style={{
            position:   'relative',
            display:    'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap:         24,
            textAlign:  'center',
            padding:    '0 32px',
            animation:  'spectre-emerge 0.7s ease-out forwards',
          }}>

            {/* Silhouette étoile */}
            <div style={{ position: 'relative' }}>
              <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
                <path
                  d="M60 10 L68 44 L100 44 L75 65 L84 100 L60 80 L36 100 L45 65 L20 44 L52 44 Z"
                  stroke="#FFD700" strokeWidth="1.5" fill="none" opacity="0.85"
                />
                <path
                  d="M60 24 L66 44 L86 44 L72 57 L77 78 L60 67 L43 78 L48 57 L34 44 L54 44 Z"
                  fill="rgba(255,215,0,0.10)" stroke="#9C27B0" strokeWidth="0.5"
                />
                <circle cx="60" cy="60" r="9"  fill="#FFD700" opacity="0.55" />
                <circle cx="60" cy="60" r="4"  fill="#FFD700" opacity="0.95" />
              </svg>
              {/* Glow derrière l'étoile */}
              <div style={{
                position:   'absolute',
                inset:       0,
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(255,215,0,0.22) 0%, transparent 65%)',
                pointerEvents: 'none',
              }} />
            </div>

            {/* Titre */}
            {showTitle && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                <p style={{
                  fontSize:      11,
                  fontWeight:    500,
                  letterSpacing: '0.4em',
                  textTransform: 'uppercase',
                  color:         '#9C27B0',
                  margin:         0,
                }}>
                  Grade 5
                </p>

                <h1 style={{
                  fontSize:      52,
                  fontWeight:    700,
                  color:         '#FFD700',
                  margin:         0,
                  textShadow:   '0 0 32px rgba(255,215,0,0.45)',
                  animation:    'spectre-title 0.6s ease-out forwards',
                }}>
                  SPECTRE
                </h1>

                {/* Nom du vaisseau (RARE+) */}
                {data.ship_name && (
                  <p style={{
                    fontSize:   18,
                    fontWeight: 500,
                    color:      'rgba(255,255,255,0.65)',
                    margin:      0,
                    marginTop:   4,
                  }}>
                    {data.ship_name}
                  </p>
                )}

                {/* Bonus Grade 5 */}
                <p style={{
                  fontSize:   13,
                  color:      'rgba(255,255,255,0.35)',
                  margin:      0,
                  marginTop:   8,
                  maxWidth:    260,
                }}>
                  +30% toutes stats · +1 slot premium · Furtivité +10%
                </p>
              </div>
            )}

            {/* Hint fermeture */}
            <p style={{
              position:      'absolute',
              bottom:        -56,
              left:           '50%',
              transform:     'translateX(-50%)',
              fontSize:       10,
              letterSpacing: '0.1em',
              color:         'rgba(255,255,255,0.18)',
              whiteSpace:    'nowrap',
              margin:         0,
            }}>
              Cliquer pour continuer
            </p>
          </div>
        )}
      </div>
    </>
  )
}