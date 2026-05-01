// ─── App.tsx — Version finale unifiée
// Combine : routes originales (hangar/:id) + Sprint 3 (combat) + Sprint 4 (alliances)

import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore }    from '@/stores/authStore'
import { AppLayout }       from '@/components/layout/AppLayout'
import { LoginPage }       from '@/pages/LoginPage'
import { DashboardPage }   from '@/pages/DashboardPage'
import { HangarPage }      from '@/pages/HangarPage'
import { ShipDetailPage }  from '@/pages/ShipDetailPage'
import { ForgePage }       from '@/pages/ForgePage'
import { GalaxyPage }      from '@/pages/GalaxyPage'
import { RankingPage }     from '@/pages/RankingPage'
import { PlanetPage }      from '@/pages/PlanetPage'
import { BuildingsPage }   from '@/pages/BuildingsPage'
import { ExpeditionPage }  from '@/pages/ExpeditionPage'
import { TechPage }        from '@/pages/TechPage'
import { CombatsPage }     from '@/pages/CombatsPage'
import { CombatReportPage } from '@/pages/CombatReportPage'
import { AlliancesPage }   from '@/pages/AlliancesPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuthStore()
  const location = useLocation()
  if (!accessToken) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

function RedirectIfAuth({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuthStore()
  if (accessToken) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<RedirectIfAuth><LoginPage /></RedirectIfAuth>} />

        <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Pages principales */}
          <Route path="/dashboard"    element={<DashboardPage />} />
          <Route path="/planets/:id"  element={<PlanetPage />} />
          <Route path="/buildings"    element={<BuildingsPage />} />

          {/* Hangar — /hangar/:id pour le détail vaisseau (HangarPage navigue vers /hangar/:id) */}
          <Route path="/hangar"       element={<HangarPage />} />
          <Route path="/hangar/:id"   element={<ShipDetailPage />} />

          {/* Forge, Galaxie, Classement */}
          <Route path="/forge"        element={<ForgePage />} />
          <Route path="/galaxy"       element={<GalaxyPage />} />
          <Route path="/ranking"      element={<RankingPage />} />

          {/* Technologies & Expéditions */}
          <Route path="/expeditions"  element={<ExpeditionPage />} />
          <Route path="/tech"         element={<TechPage />} />

          {/* Combat — /combat = liste, /combat/:id = rapport (ordre important) */}
          <Route path="/combat"       element={<CombatsPage />} />
          <Route path="/combat/:id"   element={<CombatReportPage />} />

          {/* Alliances */}
          <Route path="/alliances"    element={<AlliancesPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
