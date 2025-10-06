import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type { Order, ComposeOrder, CreateOrderData } from '@/types'

export const ordersService = {
  async getAll(): Promise<any[]> {
    const response = await apiClient.get<any[]>(API_ENDPOINTS.ORDERS.ALL)
    return response.data
  },

  async getById(id: number): Promise<Order> {
    const response = await apiClient.get<Order>(
      API_ENDPOINTS.ORDERS.DETAIL(id)
    )
    return response.data
  },

  async create(data: CreateOrderData): Promise<Order> {
    const response = await apiClient.post<Order>(
      API_ENDPOINTS.ORDERS.CREATE,
      data
    )
    return response.data
  },

  async save(data: any): Promise<any> {
    const response = await apiClient.post(API_ENDPOINTS.ORDERS.SAVE, data)
    return response.data
  },

  async generatePdf(id: number): Promise<{ pdf_path: string }> {
    const response = await apiClient.post<{ pdf_path: string }>(
      API_ENDPOINTS.ORDERS.GENERATE_PDF(id)
    )
    return response.data
  },

  // Compose Orders
  async saveComposeOrder(data: any): Promise<any> {
    const response = await apiClient.post(
      API_ENDPOINTS.COMPOSE_ORDERS.SAVE,
      data
    )
    return response.data
  },

  async getComposeOrderById(id: number): Promise<ComposeOrder> {
    const response = await apiClient.get<ComposeOrder>(
      API_ENDPOINTS.COMPOSE_ORDERS.DETAIL(id)
    )
    return response.data
  },

  async deleteComposeOrder(id: number): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.COMPOSE_ORDERS.DELETE(id))
  },

  async generateComposeOfferPdf(data: any): Promise<any> {
    const response = await apiClient.post(
      API_ENDPOINTS.COMPOSE_ORDERS.GENERATE_PDF,
      data
    )
    return response.data
  },
}