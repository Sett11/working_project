import apiClient from '../client'
import { API_ENDPOINTS } from '../endpoints'
import type {
  LoginCredentials,
  RegisterData,
  TokenResponse,
  UserResponse,
} from '@/types'

export const authService = {
  async register(data: RegisterData): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>(
      API_ENDPOINTS.AUTH.REGISTER,
      data
    )
    return response.data
  },

  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>(
      API_ENDPOINTS.AUTH.LOGIN,
      credentials
    )
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT)
  },

  async getCurrentUser(): Promise<UserResponse> {
    const response = await apiClient.get<UserResponse>(API_ENDPOINTS.AUTH.ME)
    return response.data
  },
}