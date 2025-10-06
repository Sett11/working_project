export interface Component {
  id: number
  name: string
  category: string
  category_folder?: string
  size?: string
  characteristics?: string
  price: number
  manufacturer?: string
  in_stock: boolean
  description?: string
  image_path?: string
  currency?: string
  material?: string
  standard?: string
}

export type ComponentCategory =
  | 'Трубы'
  | 'Теплоизоляция'
  | 'Кронштейны'
  | 'Дренажные системы'
  | 'Кабели и провода'
  | 'Кабель-каналы'
  | 'Комплектующие кабель-каналов'