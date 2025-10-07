import type { Client, CreateClientData } from './client.types'

// Только Compose Order используется в системе
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