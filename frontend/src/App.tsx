import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { AppLayout }      from '@/components/layout/AppLayout'
import { LoginPage }      from '@/pages/LoginPage'
import { DashboardPage }  from '@/pages/DashboardPage'
import { HangarPage }     from '@/pages/HangarPage'
import { ShipDetailPage } from '@/pages/ShipDetailPage'
import { ForgePage }      from '@/pages/ForgePage'
import { GalaxyPage }     from '@/pages/GalaxyPage'
import { RankingPage }    from '@/pages/RankingPage'
import { PlanetPage }     from '@/pages/PlanetPage'
import { BuildingsPage }  from '@/pages/BuildingsPage'

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
          <Route path="/dashboard"   element={<DashboardPage />} />
          <Route path="/planets/:id" element={<PlanetPage />} />
          <Route path="/buildings"   element={<BuildingsPage />} />
          <Route path="/hangar"      element={<HangarPage />} />
          <Route path="/hangar/:id"  element={<ShipDetailPage />} />
          <Route path="/forge"       element={<ForgePage />} />
          <Route path="/galaxy"      element={<GalaxyPage />} />
          <Route path="/ranking"     element={<RankingPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
