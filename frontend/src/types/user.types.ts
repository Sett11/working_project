export interface User {
  id: number
  username: string
  email?: string
  created_at: string
  last_login?: string
  is_active: boolean
  is_admin?: boolean
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  password: string
  secret_key?: string
}

export interface TokenResponse {
  token: string
  expires_at: string
  user: User
}

export interface UserResponse {
  id: number
  username: string
  email?: string
  is_active: boolean
  created_at: string
}