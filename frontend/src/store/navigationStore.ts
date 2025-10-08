import { create } from 'zustand'
import type { NavigateFunction } from 'react-router-dom'

/**
 * Navigation Store
 * 
 * Manages navigation state using Zustand instead of module-level global variable.
 * This approach provides:
 * - No global mutable state (SSR/HMR safe)
 * - Type-safe access to navigate function
 * - Imperative navigation outside React components
 * - Consistent with project's state management pattern
 */
interface NavigationState {
  /** React Router's navigate function */
  navigate: NavigateFunction | null
  
  /** Set the navigate function (called once from root component) */
  setNavigate: (navigate: NavigateFunction) => void
}

export const useNavigationStore = create<NavigationState>(set => ({
  navigate: null,
  
  setNavigate: navigate => set({ navigate }),
}))
