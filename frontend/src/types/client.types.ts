export interface Client {
  id: number
  full_name: string
  phone: string
  email?: string
  address?: string
}

export interface CreateClientData {
  full_name: string
  phone: string
  email?: string
  address?: string
}