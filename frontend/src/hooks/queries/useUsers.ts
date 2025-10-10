import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { usersService } from '@/api/services/users.service'
import { useNotificationStore } from '@/store/notificationStore'
import { extractErrorMessage } from '@/utils'
import type { UserResponse } from '@/types'
import type { AxiosError } from 'axios'

/**
 * Query Keys для запросов пользователей
 * Централизованный для консистентности и легкой инвалидации
 */
export const usersKeys = {
  all: ['users'] as const,
  lists: () => [...usersKeys.all, 'list'] as const,
  list: () => [...usersKeys.lists()] as const,
}

/**
 * Hook для получения списка всех пользователей
 * Автоматически кэширует и рефетчит при фокусе окна
 * Показывает уведомления об ошибках через notificationStore
 * 
 * Требует прав администратора на backend
 */
export function useUsers() {
  const { showError } = useNotificationStore()
  
  const query = useQuery<UserResponse[], AxiosError>({
    queryKey: usersKeys.list(),
    queryFn: usersService.getAll,
    // Держим данные свежими 5 минут
    staleTime: 5 * 60 * 1000,
    // Рефетчим при фокусе окна
    refetchOnWindowFocus: true,
  })

  // Обработка ошибок через useEffect
  React.useEffect(() => {
    if (query.error) {
      const error = query.error as AxiosError
      
      // Логируем ошибку для отладки
      console.error('Failed to load users:', error)
      
      // Показываем пользователю уведомление об ошибке
      let errorMessage = 'Не удалось загрузить список пользователей'
      
      // Специальная обработка для 403 (нет прав)
      if (error.response?.status === 403) {
        errorMessage = 'Доступ запрещен. Требуются права администратора.'
      } else {
        // Извлекаем сообщение об ошибке из ответа
        errorMessage = extractErrorMessage(error, errorMessage)
      }
      
      showError(errorMessage)
    }
  }, [query.error, showError])

  return query
}
