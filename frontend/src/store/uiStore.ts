import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Language = 'ru' | 'en'
type Theme = 'light' | 'dark'

interface UIState {
  language: Language
  theme: Theme
  sidebarOpen: boolean

  setLanguage: (lang: Language) => void
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    set => ({
      language: 'ru',
      theme: 'dark',
      sidebarOpen: false,

      setLanguage: language => set({ language }),

      setTheme: theme => set({ theme }),

      toggleTheme: () =>
        set(state => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),

      toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),

      setSidebarOpen: open => set({ sidebarOpen: open }),
    }),
    {
      name: 'ui-storage',
      partialize: state => ({
        language: state.language,
        theme: state.theme,
      }),
    }
  )
)