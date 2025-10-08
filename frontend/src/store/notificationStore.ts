import { create } from 'zustand'

/**
 * Notification Types
 * - success: Успешное выполнение операции (зеленый)
 * - error: Ошибка выполнения (красный)
 * - warning: Предупреждение (оранжевый)
 * - info: Информационное сообщение (синий)
 */
export type NotificationSeverity = 'success' | 'error' | 'warning' | 'info'

/**
 * Notification State
 */
interface Notification {
  /** Уникальный ID уведомления */
  id: string
  /** Сообщение для отображения */
  message: string
  /** Тип уведомления */
  severity: NotificationSeverity
  /** Длительность отображения в мс (по умолчанию 6000) */
  duration?: number
}

interface NotificationState {
  /** Текущее активное уведомление (показывается только одно) */
  notification: Notification | null
  
  /** Показать уведомление */
  showNotification: (message: string, severity: NotificationSeverity, duration?: number) => void
  
  /** Закрыть текущее уведомление */
  hideNotification: () => void
  
  /** Вспомогательные методы для часто используемых типов */
  showSuccess: (message: string, duration?: number) => void
  showError: (message: string, duration?: number) => void
  showWarning: (message: string, duration?: number) => void
  showInfo: (message: string, duration?: number) => void
}

/**
 * Notification Store
 * 
 * Централизованное управление уведомлениями (Snackbar) в приложении.
 * Использует паттерн "одно уведомление за раз" для лучшего UX.
 * 
 * Пример использования:
 * ```tsx
 * const { showSuccess, showError } = useNotificationStore()
 * 
 * // Показать успешное уведомление
 * showSuccess('Операция выполнена успешно')
 * 
 * // Показать ошибку
 * showError('Произошла ошибка')
 * ```
 */
export const useNotificationStore = create<NotificationState>((set) => ({
  notification: null,
  
  showNotification: (message, severity, duration = 6000) => {
    const id = Date.now().toString()
    set({
      notification: {
        id,
        message,
        severity,
        duration,
      },
    })
  },
  
  hideNotification: () => {
    set({ notification: null })
  },
  
  // Вспомогательные методы
  showSuccess: (message, duration) => {
    useNotificationStore.getState().showNotification(message, 'success', duration)
  },
  
  showError: (message, duration) => {
    useNotificationStore.getState().showNotification(message, 'error', duration)
  },
  
  showWarning: (message, duration) => {
    useNotificationStore.getState().showNotification(message, 'warning', duration)
  },
  
  showInfo: (message, duration) => {
    useNotificationStore.getState().showNotification(message, 'info', duration)
  },
}))

