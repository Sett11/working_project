import type { NavigateFunction } from 'react-router-dom'

// Глобальная ссылка на функцию навигации
let navigateFunction: NavigateFunction | null = null

/**
 * Инициализирует глобальную функцию навигации
 * Должна быть вызвана из корневого компонента с помощью useNavigate()
 */
export const setNavigate = (navigate: NavigateFunction) => {
  navigateFunction = navigate
}

/**
 * Навигация без перезагрузки страницы (SPA-стиль)
 * Использует replace по умолчанию, чтобы не добавлять запись в историю
 */
export const navigateTo = (path: string, replace = true) => {
  if (navigateFunction) {
    navigateFunction(path, { replace })
  } else {
    // Fallback на window.location, если navigate не инициализирован
    console.warn('Navigate function not initialized, falling back to window.location')
    if (replace) {
      window.location.replace(path)
    } else {
      window.location.href = path
    }
  }
}

