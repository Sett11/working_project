import React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authService } from '@/api/services/auth.service'
import { useAuthStore } from '@/store/authStore'
import { useNotificationStore } from '@/store/notificationStore'
import { extractErrorMessage } from '@/utils'
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
  const { showError } = useNotificationStore()
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
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Login failed:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Ошибка входа. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
    },
  })
}

/**
 * Hook for registration mutation
 * Automatically updates auth store and redirects on success
 * Uses React.useRef to track timeout and clean it up on unmount
 */
export function useRegister() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const { showSuccess, showError } = useNotificationStore()
  const queryClient = useQueryClient()
  
  // Track timeout ID to prevent memory leak on unmount
  const timeoutRef = React.useRef<number | null>(null)
  
  // Cleanup timeout on unmount
  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])
  
  return useMutation({
    mutationFn: (data: RegisterData) => authService.register(data),
    onSuccess: (data) => {
      // Show success notification
      showSuccess('Регистрация успешно завершена! Добро пожаловать!')
      
      // Update auth store with user and token
      setAuth(data.user, data.token)
      
      // Invalidate and refetch current user query
      queryClient.invalidateQueries({ queryKey: authKeys.currentUser() })
      
      // Navigate to home page after short delay
      // Store timeout ID for cleanup
      timeoutRef.current = setTimeout(() => {
        navigate('/', { replace: true })
        timeoutRef.current = null
      }, 1500)
    },
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Registration failed:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Ошибка регистрации. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
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
 * Automatically clears auth store, cache, and redirects to login on success
 * Shows error notification without clearing auth on failure
 * Uses React.useRef to track timeout and clean it up on unmount
 */
export function useDeleteAccount() {
  const navigate = useNavigate()
  const { clearAuth } = useAuthStore()
  const { showSuccess, showError } = useNotificationStore()
  const queryClient = useQueryClient()
  
  // Track timeout ID to prevent memory leak on unmount
  const timeoutRef = React.useRef<number | null>(null)
  
  // Cleanup timeout on unmount
  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])
  
  return useMutation({
    mutationFn: authService.deleteAccount,
    onSuccess: () => {
      // Show success notification
      showSuccess('Аккаунт успешно удален')
      
      // Clear auth store
      clearAuth()
      
      // Clear all queries from cache
      queryClient.clear()
      
      // Navigate to login page after short delay to let user see the notification
      // Store timeout ID for cleanup
      timeoutRef.current = setTimeout(() => {
        navigate('/login', { replace: true })
        timeoutRef.current = null
      }, 1000)
    },
    onError: (error: unknown) => {
      // Log the error for debugging
      console.error('Account deletion failed:', error)
      
      // Show user-facing error message
      const errorMessage = extractErrorMessage(error, 'Не удалось удалить аккаунт. Пожалуйста, попробуйте снова.')
      showError(errorMessage)
      
      // Do NOT clear auth or navigate on error - user stays logged in
    },
  })
}
