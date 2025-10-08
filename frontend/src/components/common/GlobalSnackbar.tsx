import { Snackbar, Alert } from '@mui/material'
import { useNotificationStore } from '@/store/notificationStore'

/**
 * GlobalSnackbar Component
 * 
 * Глобальный компонент для отображения уведомлений (toast-сообщений).
 * Управляется через Zustand store (useNotificationStore).
 * 
 * Особенности:
 * - Автоматически закрывается через заданное время
 * - Поддерживает 4 типа: success, error, warning, info
 * - Позиционируется в нижнем центре экрана
 * - Можно закрыть вручную
 * 
 * Использование:
 * Добавьте компонент в корень приложения (main.tsx или App.tsx),
 * затем вызывайте методы из useNotificationStore в любом месте приложения:
 * 
 * ```tsx
 * const { showSuccess, showError } = useNotificationStore()
 * showSuccess('Успешно!')
 * showError('Ошибка!')
 * ```
 */
export default function GlobalSnackbar() {
  const { notification, hideNotification } = useNotificationStore()

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    // Не закрывать при клике вне snackbar
    if (reason === 'clickaway') {
      return
    }
    hideNotification()
  }

  return (
    <Snackbar
      open={!!notification}
      autoHideDuration={notification?.duration || 6000}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
    >
      <Alert
        onClose={handleClose}
        severity={notification?.severity || 'info'}
        variant="filled"
        sx={{ width: '100%' }}
      >
        {notification?.message}
      </Alert>
    </Snackbar>
  )
}

