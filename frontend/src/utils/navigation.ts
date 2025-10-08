import { useNavigationStore } from '@/store/navigationStore'

/**
 * Navigate to a path without page reload (SPA-style navigation)
 * 
 * Uses Zustand store instead of global variable for better:
 * - SSR compatibility (no module-level state)
 * - HMR stability (no stale references)
 * - Testing (isolated state per test)
 * 
 * @param path - Target path to navigate to
 * @param replace - If true, replaces current history entry. Default: false (standard behavior)
 */
export const navigateTo = (path: string, replace = false) => {
  const navigate = useNavigationStore.getState().navigate
  
  if (navigate) {
    navigate(path, { replace })
  } else {
    // Fallback to History API if navigate not initialized (preserves SPA behavior)
    console.error('Navigate function not initialized, using History API fallback')
    
    if (replace) {
      window.history.replaceState(null, '', path)
    } else {
      window.history.pushState(null, '', path)
    }
    
    // Dispatch popstate event to notify React Router about the change
    window.dispatchEvent(new PopStateEvent('popstate'))
  }
}

