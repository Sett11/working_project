import { StrictMode, useMemo } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ThemeProvider, CssBaseline } from '@mui/material'
import './index.css'
import './i18n'
import AppRoutes from './routes'
import { createAppTheme } from './theme'
import { useUIStore } from './store'
import { useDocumentLang } from './hooks/useDocumentLang'
import DocumentHead from './components/common/DocumentHead'

/**
 * TanStack Query Client Configuration
 * 
 * Global settings for all queries and mutations:
 * - Automatic caching and deduplication
 * - Background refetching on window focus
 * - Retry logic for failed requests
 * - Stale time management
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Refetch when window regains focus (useful for stale data)
      refetchOnWindowFocus: true,
      // Retry failed requests once before showing error
      retry: 1,
      // Data considered fresh for 5 minutes (no refetch during this time)
      staleTime: 5 * 60 * 1000,
      // Cache data for 10 minutes after last usage
      gcTime: 10 * 60 * 1000,
      // Show stale data while refetching in background
      refetchOnMount: true,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
})

// Компонент-обёртка для провайдеров
function AppProviders() {
  const theme = useUIStore(state => state.theme)
  const muiTheme = useMemo(() => createAppTheme(theme), [theme])

  // Синхронизируем атрибут lang HTML-элемента с текущим языком i18n
  useDocumentLang()

  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      {/* Компонент для динамического обновления заголовка документа */}
      <DocumentHead />
      <AppRoutes />
    </ThemeProvider>
  )
}

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error("Root element with id 'root' not found in HTML")
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppProviders />
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </StrictMode>
)
