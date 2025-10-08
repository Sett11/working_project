import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore, useNavigationStore } from '@/store'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import NotFoundPage from '@/pages/NotFoundPage'
import LandingPage from '@/pages/LandingPage'
import App from '@/App'
import SettingsPage from '@/pages/DashboardPages/SettingsPage'
import OrdersPage from '@/pages/DashboardPages/OrdersPage'
import { Box, CircularProgress } from '@mui/material'

// Общий интерфейс для охранных компонентов маршрутов
interface RouteGuardProps {
  children: React.ReactNode
}

function ProtectedRoute({ children }: RouteGuardProps) {
  const { isAuthenticated, isAuthInitialized } = useAuthStore()
  
  // Ждем завершения инициализации аутентификации
  if (!isAuthInitialized) {
    return null
  }
  
  // Редиректим на логин только после инициализации, если не аутентифицирован
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return children
}

// Компонент для публичных маршрутов (недоступны после входа)
function AuthOnlyRoute({ children }: RouteGuardProps) {
  const { isAuthenticated, isAuthInitialized } = useAuthStore()
  
  // Показываем индикатор загрузки во время инициализации аутентификации
  if (!isAuthInitialized) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <CircularProgress />
      </Box>
    )
  }
  
  // Редиректим на dashboard только после инициализации, если аутентифицирован
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  
  return children
}

export default function AppRoutes() {
  const navigate = useNavigate()
  const setNavigate = useNavigationStore(state => state.setNavigate)
  
  // Initialize navigation function in Zustand store for imperative usage outside components
  useEffect(() => {
    setNavigate(navigate)
  }, [navigate, setNavigate])
  
  return (
    <Routes>
      {/* Публичная главная страница */}
      <Route path="/" element={<LandingPage />} />

      {/* Публичные маршруты (только для неавторизованных) */}
      <Route
        path="/login"
        element={
          <AuthOnlyRoute>
            <LoginPage />
          </AuthOnlyRoute>
        }
      />
      <Route
        path="/register"
        element={
          <AuthOnlyRoute>
            <RegisterPage />
          </AuthOnlyRoute>
        }
      />

      {/* Защищённые маршруты */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        }
      >
        <Route path="settings" element={<SettingsPage />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route index element={<Navigate to="/dashboard/orders?filter=my" replace />} />
      </Route>

      {/* Страница 404 для всех остальных маршрутов */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
