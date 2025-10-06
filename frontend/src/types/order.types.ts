import type { Client, CreateClientData } from './client.types'

export interface Order {
  id: number
  status: 'draft' | 'ready'
  pdf_path?: string
  order_data: OrderData
  order_type: 'Order' | 'Compose'
  created_at: string
  client_id: number
  client?: Client
}

export interface OrderData {
  air_conditioners?: OrderAirConditioner[]
  components?: OrderComponent[]
  installation_params?: InstallationParams
  client_data?: CreateClientData
}

export interface OrderAirConditioner {
  id: number
  quantity: number
  price: number
}

export interface OrderComponent {
  id: number
  quantity: number
  price: number
}

export interface InstallationParams {
  route_length?: number
  floor?: number
  additional_services?: string[]
}

export interface CreateOrderData {
  client_data: CreateClientData
  order_params?: OrderData
  aircon_params?: any
  components?: any[]
  status?: 'draft' | 'ready'
}

export interface ComposeOrder {
  id: number
  user_id: number
  status: 'draft' | 'ready'
  pdf_path?: string
  compose_order_data: ComposeOrderData
  order_type: 'Compose'
  created_at: string
  client_id?: number
  client?: Client
}

export interface ComposeOrderData {
  client_data?: CreateClientData
  rooms?: RoomData[]
}

export interface RoomData {
  selected_aircons_for_room?: any[]
  components_for_room?: any[]
}