import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/authStore'
import { ApiError } from '@/lib/api'

// Étoiles générées statiquement
const STARS = Array.from({ length: 80 }, (_, i) => ({
  id: i,
  x: Math.sin(i * 13.7) * 50 + 50,
  y: Math.sin(i * 7.3) * 50 + 50,
  size: Math.sin(i * 3.1) * 1.5 + 1,
  opacity: Math.sin(i * 5.7) * 0.3 + 0.3,
  delay: (i % 10) * 0.5,
}))

export function LoginPage() {
  const navigate = useNavigate()
  const { setTokens } = useAuthStore()
  const [tab, setTab]           = useState<'login' | 'register'>('login')
  const [loading, setLoading]   = useState(false)
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [mounted, setMounted]   = useState(false)

  useEffect(() => { setTimeout(() => setMounted(true), 100) }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const res = tab === 'login'
        ? await authApi.login(email, password)
        : await authApi.register(username, email, password)
      setTokens(res.access_token, res.refresh_token)
      navigate('/dashboard')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">

      {/* Fond spatial */}
      <div className="fixed inset-0 bg-void" />

      {/* Nébuleuse */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0" style={{
          background: 'radial-gradient(ellipse 80% 60% at 15% 20%, rgba(45,125,210,0.08) 0%, transparent 60%)',
        }} />
        <div className="absolute inset-0" style={{
          background: 'radial-gradient(ellipse 60% 50% at 85% 80%, rgba(124,58,237,0.06) 0%, transparent 60%)',
        }} />
        <div className="absolute inset-0" style={{
          background: 'radial-gradient(ellipse 40% 30% at 50% 50%, rgba(6,182,212,0.04) 0%, transparent 60%)',
        }} />
      </div>

      {/* Étoiles */}
      <div className="fixed inset-0 pointer-events-none">
        {STARS.map(star => (
          <div key={star.id}
            className="absolute rounded-full"
            style={{
              left: `${star.x}%`, top: `${star.y}%`,
              width: `${star.size}px`, height: `${star.size}px`,
              background: 'white',
              opacity: star.opacity,
              boxShadow: star.size > 2 ? '0 0 4px rgba(255,255,255,0.4)' : 'none',
            }} />
        ))}
      </div>

      {/* Contenu */}
      <div className={`relative w-full max-w-md transition-all duration-700 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>

        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="font-display font-black text-6xl tracking-wider mb-3">
            <span className="text-white">EM</span>
            <span style={{ color: '#2d7dd2', textShadow: '0 0 30px rgba(45,125,210,0.8), 0 0 60px rgba(45,125,210,0.3)' }}>AGO</span>
          </h1>
          <div className="h-px max-w-32 mx-auto mb-3"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(45,125,210,0.6), transparent)' }} />
          <p className="text-[11px] text-gray-500 uppercase tracking-widest font-display">
            Conquête Spatiale · Multijoueur
          </p>
        </div>

        {/* Card */}
        <div className="rounded-2xl overflow-hidden"
          style={{
            background: 'rgba(8,12,24,0.85)',
            border: '1px solid rgba(45,125,210,0.2)',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 0 60px rgba(45,125,210,0.1), 0 25px 50px rgba(0,0,0,0.5)',
          }}>

          {/* Ligne supérieure */}
          <div className="h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(45,125,210,0.8), transparent)' }} />

          <div className="p-8">
            {/* Tabs */}
            <div className="flex mb-7 p-1 rounded-lg" style={{ background: 'rgba(15,22,40,0.8)' }}>
              {(['login', 'register'] as const).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className="flex-1 py-2.5 text-sm font-display tracking-wider rounded-md transition-all duration-200"
                  style={tab === t ? {
                    background: 'linear-gradient(135deg, rgba(45,125,210,0.2), rgba(45,125,210,0.1))',
                    border: '1px solid rgba(45,125,210,0.3)',
                    color: '#60a5fa',
                    boxShadow: '0 0 10px rgba(45,125,210,0.2)',
                  } : { color: '#6b7280' }}>
                  {t === 'login' ? 'CONNEXION' : 'INSCRIPTION'}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {tab === 'register' && (
                <div>
                  <label className="section-title block mb-1.5">Nom de commandant</label>
                  <input className="input-field" placeholder="3–32 caractères"
                    value={username} onChange={e => setUsername(e.target.value)}
                    required minLength={3} maxLength={32} />
                </div>
              )}
              <div>
                <label className="section-title block mb-1.5">Email</label>
                <input type="email" className="input-field" placeholder="votre@email.com"
                  value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
              <div>
                <label className="section-title block mb-1.5">Mot de passe</label>
                <input type="password" className="input-field"
                  placeholder={tab === 'register' ? '8 caractères minimum' : ''}
                  value={password} onChange={e => setPassword(e.target.value)}
                  required minLength={tab === 'register' ? 8 : 1} />
              </div>

              <button type="submit" disabled={loading} className="btn-primary w-full py-3 mt-2 text-base font-display tracking-widest">
                {loading ? '⏳ CHARGEMENT...' : tab === 'login' ? '⚡ SE CONNECTER' : '🚀 REJOINDRE L\'EMPIRE'}
              </button>
            </form>

            {/* Description */}
            <p className="text-center text-[10px] text-gray-700 mt-6 leading-relaxed">
              Stratégie spatiale temps réel · Vaisseaux RPG uniques<br />
              Combats · Forge · Alliances · Zéro pay-to-win
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
