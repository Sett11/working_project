import type { ComponentCategory } from '@/types'

export const API_ENDPOINTS = {
  // Auth
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    ME: '/auth/me',
    DELETE_ACCOUNT: '/auth/delete',
  },

  // Air Conditioners (не используются в текущей версии, но оставлены для будущего)
  AIR_CONDITIONERS: {
    LIST: '/air-conditioners',
    DETAIL: (id: number) => `/air-conditioners/${id}`,
  },

  // Components (не используются в текущей версии, но оставлены для будущего)
  COMPONENTS: {
    LIST: '/components',
    DETAIL: (id: number) => `/components/${id}`,
    BY_CATEGORY: (category: ComponentCategory) => `/components/category/${category}`,
  },

  // Clients (не используются в текущей версии, но оставлены для будущего)
  CLIENTS: {
    LIST: '/clients',
    CREATE: '/clients',
    DETAIL: (id: number) => `/clients/${id}`,
  },

  // Compose Orders (единственный тип заказов в системе)
  COMPOSE_ORDERS: {
    SAVE: '/save_compose_order/',
    DETAIL: (id: number) => `/compose_order/${id}`,
    DELETE: (id: number) => `/compose_order/${id}`,
    GENERATE_PDF: (id: number) => `/compose_order/${id}/generate-pdf`,
  },

  // Air Conditioner Selection
  SELECT_AIRCONS: '/select_aircons/',

  // System
  HEALTH: '/health',
  MONITORING: {
    STATUS: '/monitoring/status',
    START: '/monitoring/start',
    STOP: '/monitoring/stop',
    CONTROL: '/monitoring/control',
  },
} as const
