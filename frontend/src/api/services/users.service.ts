import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type { UserResponse } from '@/types'

/**
 * Сервис для работы с пользователями (только для администраторов)
 */
export const usersService = {
  /**
   * Получение списка всех пользователей
   * Требует прав администратора
   */
  async getAll(): Promise<UserResponse[]> {
    const response = await apiClient.get<UserResponse[]>(API_ENDPOINTS.USERS.LIST)
    return response.data
  },
}
