import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ENV } from '@/config/env'

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
    const token = localStorage.getItem('auth_token')
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
    // Обработка ошибки 401 (неавторизован)
    if (error.response?.status === 401) {
      // Удаляем токен
      localStorage.removeItem('auth_token')
      
      // Перенаправляем на логин, если не находимся на странице логина
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
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