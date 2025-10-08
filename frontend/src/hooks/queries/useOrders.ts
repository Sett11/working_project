import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { composeOrdersService } from '@/api/services/orders.service'
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
 */
export function useSaveOrder() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: any) => composeOrdersService.save(data),
    onSuccess: () => {
      // Invalidate orders list to refetch
      queryClient.invalidateQueries({ queryKey: ordersKeys.lists() })
    },
  })
}

/**
 * Hook for deleting an order
 * Automatically invalidates orders list and removes detail from cache
 */
export function useDeleteOrder() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => composeOrdersService.delete(id),
    onSuccess: (_, deletedId) => {
      // Remove deleted order from cache
      queryClient.removeQueries({ queryKey: ordersKeys.detail(deletedId) })
      
      // Invalidate orders list to refetch
      queryClient.invalidateQueries({ queryKey: ordersKeys.lists() })
    },
  })
}

/**
 * Hook for generating PDF for an order
 * Automatically updates order detail in cache on success
 */
export function useGeneratePdf() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => composeOrdersService.generatePdf(id),
    onSuccess: (_, orderId) => {
      // Invalidate order detail to refetch updated data
      queryClient.invalidateQueries({ queryKey: ordersKeys.detail(orderId) })
    },
  })
}
