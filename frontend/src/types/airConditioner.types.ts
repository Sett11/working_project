export interface AirConditioner {
  id: number
  model_name: string
  brand: string
  mount_type?: string
  cooling_power_kw?: number
  retail_price_byn: number
  is_inverter: boolean
  has_wifi: boolean
  image_path?: string
  description?: string
  series?: string
  energy_efficiency_class?: string
}