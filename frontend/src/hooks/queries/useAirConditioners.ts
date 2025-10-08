import { useMutation, useQuery } from '@tanstack/react-query'
import { airConditionersService } from '@/api/services/airConditioners.service'
import { useNotificationStore } from '@/store/notificationStore'
import { extractErrorMessage } from '@/utils'
import type { AirconSelectParams } from '@/types'

/**
 * Query Keys for Air Conditioners-related queries
 * Centralized to ensure consistency and easy invalidation
 */
export const airConditionersKeys = {
  all: ['airConditioners'] as const,
  lists: () => [...airConditionersKeys.all, 'list'] as const,
  list: (filters?: string) => [...airConditionersKeys.lists(), { filters }] as const,
  details: () => [...airConditionersKeys.all, 'detail'] as const,
  detail: (id: number) => [...airConditionersKeys.details(), id] as const,
  selection: () => [...airConditionersKeys.all, 'selection'] as const,
}

/**
 * Hook for fetching all air conditioners
 * Automatically caches and refetches on window focus
 */
export function useAirConditioners() {
  return useQuery({
    queryKey: airConditionersKeys.list(),
    queryFn: airConditionersService.getAll,
    // Keep data fresh for 10 minutes (product catalog doesn't change often)
    staleTime: 10 * 60 * 1000,
    // Refetch on window focus
    refetchOnWindowFocus: true,
  })
}

/**
 * Hook for fetching a single air conditioner by ID
 * Automatically caches and refetches on window focus
 */
export function useAirConditioner(id: number) {
  return useQuery({
    queryKey: airConditionersKeys.detail(id),
    queryFn: () => airConditionersService.getById(id),
    // Keep data fresh for 10 minutes
    staleTime: 10 * 60 * 1000,
    // Only fetch if id is valid
    enabled: id > 0,
  })
}

/**
 * Hook for selecting air conditioners based on parameters
 * Uses mutation instead of query because it's a POST request with body
 * Shows error notification on failure
 */
export function useSelectAirConditioners() {
  const { showError } = useNotificationStore()
  
  return useMutation({
    mutationFn: (params: AirconSelectParams) => 
      airConditionersService.selectAircons(params),
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Failed to select air conditioners:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Не удалось подобрать кондиционеры. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
    },
  })
}
