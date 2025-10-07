import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type {
  AirConditioner,
  AirconSelectParams,
  AirconSelectResponse,
} from '@/types'

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

  /**
   * Подбор кондиционеров по заданным параметрам
   * @param airconParams - параметры для подбора кондиционеров
   * @returns объект с общим количеством и списком подобранных кондиционеров
   */
  async selectAircons(
    airconParams: AirconSelectParams
  ): Promise<AirconSelectResponse> {
    const response = await apiClient.post<AirconSelectResponse>(
      API_ENDPOINTS.SELECT_AIRCONS,
      {
        aircon_params: airconParams,
      }
    )
    return response.data
  },
}