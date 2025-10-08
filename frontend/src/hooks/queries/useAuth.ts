import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authService } from '@/api/services/auth.service'
import { useAuthStore } from '@/store/authStore'
import type { LoginCredentials, RegisterData } from '@/types'

/**
 * Query Keys for Auth-related queries
 * Centralized to ensure consistency and easy invalidation
 */
export const authKeys = {
  all: ['auth'] as const,
  currentUser: () => [...authKeys.all, 'current-user'] as const,
}

/**
 * Hook for fetching current user data
 * Automatically refetches on window focus and mounts
 */
export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore()
  
  return useQuery({
    queryKey: authKeys.currentUser(),
    queryFn: authService.getCurrentUser,
    // Only fetch if user is authenticated
    enabled: isAuthenticated,
    // Refetch on window focus to catch external changes
    refetchOnWindowFocus: true,
    // Keep data fresh for 2 minutes
    staleTime: 2 * 60 * 1000,
  })
}

/**
 * Hook for login mutation
 * Automatically updates auth store and redirects on success
 */
export function useLogin() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => authService.login(credentials),
    onSuccess: (data) => {
      // Update auth store with user and token
      setAuth(data.user, data.token)
      
      // Invalidate and refetch current user query
      queryClient.invalidateQueries({ queryKey: authKeys.currentUser() })
      
      // Navigate to home page
      navigate('/', { replace: true })
    },
  })
}

/**
 * Hook for registration mutation
 * Automatically updates auth store and redirects on success
 */
export function useRegister() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: RegisterData) => authService.register(data),
    onSuccess: (data) => {
      // Update auth store with user and token
      setAuth(data.user, data.token)
      
      // Invalidate and refetch current user query
      queryClient.invalidateQueries({ queryKey: authKeys.currentUser() })
      
      // Navigate to home page after short delay
      setTimeout(() => {
        navigate('/', { replace: true })
      }, 1500)
    },
  })
}

/**
 * Hook for logout mutation
 * Automatically clears auth store and redirects to login
 */
export function useLogout() {
  const navigate = useNavigate()
  const { clearAuth } = useAuthStore()
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      // Clear auth store
      clearAuth()
      
      // Clear all queries from cache
      queryClient.clear()
      
      // Navigate to login page
      navigate('/login', { replace: true })
    },
    // Even if logout fails on server, clear local state
    onError: () => {
      clearAuth()
      queryClient.clear()
      navigate('/login', { replace: true })
    },
  })
}

/**
 * Hook for account deletion mutation
 * Automatically clears auth store and redirects to home
 */
export function useDeleteAccount() {
  const navigate = useNavigate()
  const { clearAuth } = useAuthStore()
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: authService.deleteAccount,
    onSuccess: () => {
      // Clear auth store
      clearAuth()
      
      // Clear all queries from cache
      queryClient.clear()
      
      // Navigate to home page
      navigate('/', { replace: true })
    },
  })
}
