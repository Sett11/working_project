import { useQuery } from '@tanstack/react-query'
import { componentsService } from '@/api/services/components.service'
import type { ComponentCategory } from '@/types'

/**
 * Query Keys for Components-related queries
 * Centralized to ensure consistency and easy invalidation
 */
export const componentsKeys = {
  all: ['components'] as const,
  lists: () => [...componentsKeys.all, 'list'] as const,
  list: (filters?: string) => [...componentsKeys.lists(), { filters }] as const,
  details: () => [...componentsKeys.all, 'detail'] as const,
  detail: (id: number) => [...componentsKeys.details(), id] as const,
  byCategory: (category: ComponentCategory) => 
    [...componentsKeys.all, 'category', category] as const,
}

/**
 * Hook for fetching all components
 * Automatically caches and refetches on window focus
 */
export function useComponents() {
  return useQuery({
    queryKey: componentsKeys.list(),
    queryFn: componentsService.getAll,
    // Keep data fresh for 10 minutes (product catalog doesn't change often)
    staleTime: 10 * 60 * 1000,
    // Refetch on window focus
    refetchOnWindowFocus: true,
  })
}

/**
 * Hook for fetching a single component by ID
 * Automatically caches; does not refetch on window focus
 */
export function useComponent(id: number) {
  return useQuery({
    queryKey: componentsKeys.detail(id),
    queryFn: () => componentsService.getById(id),
    // Keep data fresh for 10 minutes
    staleTime: 10 * 60 * 1000,
    // Do not refetch on window focus (detail data is stable)
    refetchOnWindowFocus: false,
    // Only fetch if id is valid
    enabled: id > 0,
  })
}

/**
 * Hook for fetching components by category
 * Automatically caches; does not refetch on window focus
 */
export function useComponentsByCategory(category: ComponentCategory) {
  return useQuery({
    queryKey: componentsKeys.byCategory(category),
    queryFn: () => componentsService.getByCategory(category),
    // Keep data fresh for 10 minutes
    staleTime: 10 * 60 * 1000,
    // Do not refetch on window focus (category data is stable)
    refetchOnWindowFocus: false,
  })
}
