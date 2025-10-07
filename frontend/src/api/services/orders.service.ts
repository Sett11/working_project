import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type { ComposeOrder } from '@/types'

/**
 * Сервис для работы с ComposeOrder (составными заказами).
 * Это единственный тип заказов в системе.
 */
export const composeOrdersService = {
  /**
   * Получение списка всех заказов
   */
  async getAll(): Promise<any[]> {
    const response = await apiClient.get<any[]>('/api/all_orders/')
    return response.data
  },

  /**
   * Сохранение составного заказа
   */
  async save(data: any): Promise<any> {
    const response = await apiClient.post(
      API_ENDPOINTS.COMPOSE_ORDERS.SAVE,
      data
    )
    return response.data
  },

  /**
   * Получение заказа по ID
   */
  async getById(id: number): Promise<ComposeOrder> {
    const response = await apiClient.get<ComposeOrder>(
      API_ENDPOINTS.COMPOSE_ORDERS.DETAIL(id)
    )
    return response.data
  },

  /**
   * Удаление заказа
   */
  async delete(id: number): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.COMPOSE_ORDERS.DELETE(id))
  },

  /**
   * Генерация PDF коммерческого предложения
   */
  async generatePdf(id: number): Promise<{ success: boolean; pdf_path?: string; error?: string }> {
    const response = await apiClient.post<{ success: boolean; pdf_path?: string; error?: string }>(
      API_ENDPOINTS.COMPOSE_ORDERS.GENERATE_PDF(id)
    )
    return response.data
  },
}

// Экспорт для обратной совместимости (если используется старое имя)
export const ordersService = composeOrdersService
