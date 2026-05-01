/**
 * App.tsx — Sprint 4 final
 * Agent 6 — Développeur Frontend
 *
 * Routes :
 *   /combat      → CombatsPage (liste des combats récents)
 *   /combat/:id  → CombatReportPage (rapport détaillé)
 *   /alliances   → AlliancesPage
 */
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AppLayout } from '@/components/layout/AppLayout'
import { useAuthStore } from '@/stores/authStore'

import { LoginPage }        from '@/pages/LoginPage'
import { DashboardPage }    from '@/pages/DashboardPage'
import { PlanetPage }       from '@/pages/PlanetPage'
import { BuildingsPage }    from '@/pages/BuildingsPage'
import { HangarPage }       from '@/pages/HangarPage'
import { ShipDetailPage }   from '@/pages/ShipDetailPage'
import { ForgePage }        from '@/pages/ForgePage'
import { GalaxyPage }       from '@/pages/GalaxyPage'
import { TechPage }         from '@/pages/TechPage'
import { ExpeditionPage }   from '@/pages/ExpeditionPage'
import { RankingPage }      from '@/pages/RankingPage'
import { CombatsPage }      from '@/pages/CombatsPage'       // ← liste combats
import { CombatReportPage } from '@/pages/CombatReportPage'  // ← détail combat
import { AlliancesPage }    from '@/pages/AlliancesPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
})

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuthStore()
  if (!accessToken) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: { background: '#1F2937', color: '#F9FAFB', border: '1px solid #374151' },
            duration: 3500,
          }}
        />
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<AuthGuard><AppLayout /></AuthGuard>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"   element={<DashboardPage />} />
            <Route path="/planet/:id"  element={<PlanetPage />} />
            <Route path="/buildings"   element={<BuildingsPage />} />
            <Route path="/hangar"      element={<HangarPage />} />
            <Route path="/ships/:id"   element={<ShipDetailPage />} />
            <Route path="/forge"       element={<ForgePage />} />
            <Route path="/galaxy"      element={<GalaxyPage />} />
            <Route path="/tech"        element={<TechPage />} />
            <Route path="/expeditions" element={<ExpeditionPage />} />
            <Route path="/ranking"     element={<RankingPage />} />
            <Route path="/alliances"   element={<AlliancesPage />} />
            {/* Combat : liste d'abord, détail ensuite — ordre important pour React Router */}
            <Route path="/combat"      element={<CombatsPage />} />
            <Route path="/combat/:id"  element={<CombatReportPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
