import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ENV } from '@/config/env'
import { navigateTo } from '@/utils/navigation'
import { useAuthStore } from '@/store/authStore'

const apiClient = axios.create({
  baseURL: ENV.API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
})

// Request interceptor - добавляем токен к каждому запросу
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Получаем токен из zustand store (который использует persist middleware)
    const token = useAuthStore.getState().token
    const user = useAuthStore.getState().user
    
    console.log('🔵 API Request:', {
      url: config.url,
      method: config.method,
      hasToken: !!token,
      user: user ? { username: user.username, is_admin: user.is_admin } : null,
    })
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor - обрабатываем 401 ошибки и другие проблемы
apiClient.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    // Логируем все ошибки для отладки
    console.log('🔴 API Error:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    })
    
    // Обработка ошибки 401 (неавторизован)
    if (error.response?.status === 401) {
      console.warn('⚠️ 401 Unauthorized - очистка состояния аутентификации')
      // Очищаем аутентификацию через zustand store (который использует persist middleware)
      useAuthStore.getState().clearAuth()
      
      // Перенаправляем на главную страницу
      if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
        navigateTo('/', true)
      }
    }
    
    // Обработка ошибки 403 (нет прав доступа) - НЕ разлогиниваем пользователя!
    if (error.response?.status === 403) {
      console.warn('⚠️ 403 Forbidden - недостаточно прав для доступа к', error.config?.url)
      // Просто пробрасываем ошибку дальше, не разлогиниваем
    }
    
    // Обработка 404 для эндпоинта /auth/me (пользователь удален из БД)
    if (error.response?.status === 404 && error.config?.url?.includes('/auth/me')) {
      console.warn('⚠️ 404 User Not Found - пользователь удален из базы, очистка состояния')
      // Очищаем аутентификацию
      useAuthStore.getState().clearAuth()
      
      // Перенаправляем на главную страницу
      if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
        navigateTo('/', true)
      }
    }
    
    // Обработка других HTTP ошибок
    if (error.response) {
      // Сервер ответил с ошибкой
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      // Запрос был отправлен, но ответа не получено
      console.error('Network Error:', error.message)
    } else {
      // Что-то пошло не так при настройке запроса
      console.error('Request Error:', error.message)
    }
    
    return Promise.reject(error)
  }
)

export default apiClient