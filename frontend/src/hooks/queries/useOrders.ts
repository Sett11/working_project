import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { composeOrdersService } from '@/api/services/orders.service'
import { useNotificationStore } from '@/store/notificationStore'
import { extractErrorMessage } from '@/utils'
import type { ComposeOrder } from '@/types'

/**
 * Query Keys for Orders-related queries
 * Centralized to ensure consistency and easy invalidation
 */
export const ordersKeys = {
  all: ['orders'] as const,
  lists: () => [...ordersKeys.all, 'list'] as const,
  list: (filters?: string) => [...ordersKeys.lists(), { filters }] as const,
  details: () => [...ordersKeys.all, 'detail'] as const,
  detail: (id: number) => [...ordersKeys.details(), id] as const,
}

/**
 * Hook for fetching all orders
 * Automatically caches and refetches on window focus
 */
export function useOrders() {
  return useQuery({
    queryKey: ordersKeys.list(),
    queryFn: composeOrdersService.getAll,
    // Keep data fresh for 3 minutes
    staleTime: 3 * 60 * 1000,
    // Refetch on window focus
    refetchOnWindowFocus: true,
  })
}

/**
 * Hook for fetching a single order by ID
 * Automatically caches and refetches on window focus
 */
export function useOrder(id: number) {
  return useQuery({
    queryKey: ordersKeys.detail(id),
    queryFn: () => composeOrdersService.getById(id),
    // Keep data fresh for 5 minutes
    staleTime: 5 * 60 * 1000,
    // Only fetch if id is valid
    enabled: id > 0,
  })
}

/**
 * Hook for creating/saving an order
 * Automatically invalidates orders list on success
 * Shows error notification on failure
 */
export function useSaveOrder() {
  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotificationStore()
  
  return useMutation({
    mutationFn: (data: ComposeOrder) => composeOrdersService.save(data),
    onSuccess: () => {
      // Show success notification
      showSuccess('Заказ успешно сохранен')
      
      // Invalidate orders list to refetch
      queryClient.invalidateQueries({ queryKey: ordersKeys.lists() })
    },
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Failed to save order:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Не удалось сохранить заказ. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
    },
  })
}

/**
 * Hook for deleting an order
 * Automatically invalidates orders list and removes detail from cache
 * Shows error notification on failure
 */
export function useDeleteOrder() {
  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotificationStore()
  
  return useMutation({
    mutationFn: (id: number) => composeOrdersService.delete(id),
    onSuccess: (_, deletedId) => {
      // Show success notification
      showSuccess('Заказ успешно удален')
      
      // Remove deleted order from cache
      queryClient.removeQueries({ queryKey: ordersKeys.detail(deletedId) })
      
      // Invalidate orders list to refetch
      queryClient.invalidateQueries({ queryKey: ordersKeys.lists() })
    },
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Failed to delete order:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Не удалось удалить заказ. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
    },
  })
}

/**
 * Hook for generating PDF for an order
 * Automatically updates order detail in cache on success
 * Shows error notification on failure
 */
export function useGeneratePdf() {
  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotificationStore()
  
  return useMutation({
    mutationFn: (id: number) => composeOrdersService.generatePdf(id),
    onSuccess: (_, orderId) => {
      // Show success notification
      showSuccess('PDF успешно сгенерирован')
      
      // Invalidate order detail to refetch updated data
      queryClient.invalidateQueries({ queryKey: ordersKeys.detail(orderId) })
    },
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Failed to generate PDF:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Не удалось сгенерировать PDF. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
    },
  })
}
