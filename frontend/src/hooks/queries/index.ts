/**
 * Centralized export for all TanStack Query hooks
 * 
 * This file provides a single entry point for all query and mutation hooks,
 * making imports cleaner and more maintainable.
 * 
 * Usage:
 * ```ts
 * import { useLogin, useOrders, useAirConditioners } from '@/hooks/queries'
 * ```
 */

// Auth hooks
export {
  useCurrentUser,
  useLogin,
  useRegister,
  useLogout,
  useDeleteAccount,
  authKeys,
} from './useAuth'

// Orders hooks
export {
  useOrders,
  useOrder,
  useSaveOrder,
  useDeleteOrder,
  useGeneratePdf,
  ordersKeys,
} from './useOrders'

// Air Conditioners hooks
export {
  useAirConditioners,
  useAirConditioner,
  useSelectAirConditioners,
  airConditionersKeys,
} from './useAirConditioners'

// Components hooks
export {
  useComponents,
  useComponent,
  useComponentsByCategory,
  componentsKeys,
} from './useComponents'
