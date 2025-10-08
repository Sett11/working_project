import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ENV } from '@/config/env'
import { navigateTo } from '@/utils/navigation'
import { useAuthStore } from '@/store/authStore'
import { useNavigationStore } from '@/store/navigationStore'

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
    // Обработка ошибки 401 (неавторизован) или 404 (пользователь не найден)
    if (error.response?.status === 401) {
      console.warn('⚠️ 401 Unauthorized - очистка состояния аутентификации')
      // Очищаем аутентификацию через zustand store (который использует persist middleware)
      useAuthStore.getState().clearAuth()
      
      // Перенаправляем на главную страницу
      if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
        navigateTo('/', true)
      }
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