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

/**
 * Параметры для подбора кондиционеров
 */
export interface AirconSelectParams {
  /** Площадь помещения (м²) */
  area: number
  /** Высота потолков (м) */
  ceiling_height?: number
  /** Уровень освещённости */
  illumination?: string
  /** Количество людей */
  num_people?: number
  /** Тип активности */
  activity?: string
  /** Количество компьютеров */
  num_computers?: number
  /** Количество телевизоров */
  num_tvs?: number
  /** Мощность другой техники (кВт) */
  other_power?: number
  /** Бренд (или "Любой") */
  brand?: string
  /** Максимальная цена (BYN) */
  price_limit?: number
  /** Инверторный тип */
  inverter?: boolean
  /** Наличие Wi-Fi */
  wifi?: boolean
  /** Тип монтажа */
  mount_type?: string
}

/**
 * Ответ от сервера при подборе кондиционеров
 */
export interface AirconSelectResponse {
  /** Общее количество найденных кондиционеров */
  total_count: number
  /** Список подобранных кондиционеров */
  aircons_list: AirConditioner[]
}