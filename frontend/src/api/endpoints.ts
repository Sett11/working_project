export const API_ENDPOINTS = {
  // Auth
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    ME: '/auth/me',
  },

  // Air Conditioners
  AIR_CONDITIONERS: {
    LIST: '/air-conditioners',
    DETAIL: (id: number) => `/air-conditioners/${id}`,
  },

  // Components
  COMPONENTS: {
    LIST: '/components',
    DETAIL: (id: number) => `/components/${id}`,
    BY_CATEGORY: (category: string) => `/components/category/${category}`,
  },

  // Clients
  CLIENTS: {
    LIST: '/clients',
    CREATE: '/clients',
    DETAIL: (id: number) => `/clients/${id}`,
  },

  // Orders
  ORDERS: {
    LIST: '/orders',
    ALL: '/all_orders/',
    CREATE: '/orders',
    SAVE: '/save_order/',
    DETAIL: (id: number) => `/orders/${id}`,
    GENERATE_PDF: (id: number) => `/orders/${id}/generate-pdf`,
  },

  // Compose Orders
  COMPOSE_ORDERS: {
    SAVE: '/save_compose_order/',
    DETAIL: (id: number) => `/compose_order/${id}`,
    DELETE: (id: number) => `/compose_order/${id}`,
    GENERATE_PDF: '/generate_compose_offer/',
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
