import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isAuthInitialized: boolean

  setAuth: (user: User, token: string) => void
  clearAuth: () => void
  updateUser: (user: Partial<User>) => void
  setAuthInitialized: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isAuthInitialized: false,

      setAuth: (user, token) => {
        set({ user, token, isAuthenticated: true })
      },

      clearAuth: () => {
        set({ user: null, token: null, isAuthenticated: false })
      },

      updateUser: user =>
        set(state => ({
          user: state.user ? { ...state.user, ...user } : null,
        })),

      setAuthInitialized: () => {
        set({ isAuthInitialized: true })
      },
    }),
    {
      name: 'auth-storage',
      partialize: state => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      // После восстановления состояния из хранилища (через persist middleware), устанавливаем флаг инициализации
      onRehydrateStorage: () => state => {
        if (state) {
          state.setAuthInitialized()
        }
      },
    }
  )
)