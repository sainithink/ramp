import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AnimateUIProvider } from '@animate-ui/react/provider'
import { Loader2 } from 'lucide-react'

// Split per route so a visitor landing on the marketing page does not download
// the assistant's audio machinery or the admin table.
const LandingPage = lazy(() => import('@/pages/landing'))
const LoginPage = lazy(() => import('@/pages/login'))
const RegisterPage = lazy(() => import('@/pages/register'))
const AssistantPage = lazy(() => import('@/pages/assistant'))
const AdminPage = lazy(() => import('@/pages/admin'))

function RouteFallback() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <Loader2 className="size-5 animate-spin text-brand" />
    </div>
  )
}

export default function App() {
  return (
    // tempo < 1 makes every Animate UI transition a little crisper, which suits
    // an interface people use for seconds at a time.
    <AnimateUIProvider tempo={0.9}>
      <BrowserRouter>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/app" element={<AssistantPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AnimateUIProvider>
  )
}
