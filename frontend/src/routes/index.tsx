import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import App from '@/App'

// Компонент для защиты маршрутов
interface ProtectedRouteProps {
  children: React.ReactNode
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

// Компонент для публичных маршрутов (недоступны после входа)
function PublicRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()
  
  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }
  
  return <>{children}</>
}

export default function AppRoutes() {
  return (
    <Routes>
      {/* Публичные маршруты */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />

      {/* Защищённые маршруты */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <App />
          </ProtectedRoute>
        }
      />

      {/* Перенаправление на логин для всех остальных маршрутов */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
