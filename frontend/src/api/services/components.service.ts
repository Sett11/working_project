import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type { Component } from '@/types'

export const componentsService = {
  async getAll(): Promise<Component[]> {
    const response = await apiClient.get<Component[]>(
      API_ENDPOINTS.COMPONENTS.LIST
    )
    return response.data
  },

  async getById(id: number): Promise<Component> {
    const response = await apiClient.get<Component>(
      API_ENDPOINTS.COMPONENTS.DETAIL(id)
    )
    return response.data
  },

  async getByCategory(category: string): Promise<Component[]> {
    const response = await apiClient.get<Component[]>(
      API_ENDPOINTS.COMPONENTS.BY_CATEGORY(category)
    )
    return response.data
  },
}