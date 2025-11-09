import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Jobs from './pages/Jobs'
import Settings from './pages/Settings'
import { useTheme } from './hooks/useTheme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const { theme } = useTheme()

  // Apply theme to HTML element
  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(theme)
  }, [theme])

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/accounts" element={<Accounts />} />
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            className: 'bg-card text-foreground border border-border',
            style: {
              background: 'hsl(var(--card))',
              color: 'hsl(var(--foreground))',
              border: '1px solid hsl(var(--border))',
            },
          }}
        />
      </QueryClientProvider>
    </div>
  )
}

export default App
