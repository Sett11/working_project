import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type { AirConditioner } from '@/types'

export const airConditionersService = {
  async getAll(): Promise<AirConditioner[]> {
    const response = await apiClient.get<AirConditioner[]>(
      API_ENDPOINTS.AIR_CONDITIONERS.LIST
    )
    return response.data
  },

  async getById(id: number): Promise<AirConditioner> {
    const response = await apiClient.get<AirConditioner>(
      API_ENDPOINTS.AIR_CONDITIONERS.DETAIL(id)
    )
    return response.data
  },

  async selectAircons(aircon_params: any): Promise<any> {
    const response = await apiClient.post(API_ENDPOINTS.SELECT_AIRCONS, {
      aircon_params,
    })
    return response.data
  },
}