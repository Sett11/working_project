import { createTheme, type ThemeOptions } from '@mui/material/styles'
import { ruRU } from '@mui/material/locale'

const getDesignTokens = (mode: 'light' | 'dark'): ThemeOptions => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          // Light mode - Ocean Green theme
          primary: {
            main: '#00897B',    // Ocean Green
            light: '#4DB6AC',   // Light Ocean Green
            dark: '#00695C',    // Dark Ocean Green
          },
          secondary: {
            main: '#00BCD4',    // Cyan (complementary color)
            light: '#62EFFF',
            dark: '#008BA3',
          },
          background: {
            default: '#f5f5f5',
            paper: '#ffffff',
          },
          text: {
            primary: 'rgba(0, 0, 0, 0.87)',
            secondary: 'rgba(0, 0, 0, 0.6)',
          },
        }
      : {
          // Dark mode - Ocean Green theme
          primary: {
            main: '#26A69A',    // Lighter Ocean Green for dark mode
            light: '#64D8CB',
            dark: '#00897B',
          },
          secondary: {
            main: '#80DEEA',    // Light Cyan for dark mode
            light: '#B2EBF2',
            dark: '#4DD0E1',
          },
          background: {
            default: '#121212',
            paper: '#1e1e1e',
          },
          text: {
            primary: '#ffffff',
            secondary: 'rgba(255, 255, 255, 0.7)',
          },
        }),
  },
  typography: {
    fontFamily: [
      '"Inter"',
      '"SF Pro Display"',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 700,
      letterSpacing: '-0.01em',
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      letterSpacing: '-0.005em',
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
      letterSpacing: '0em',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
      letterSpacing: '0.01em',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.7,
      letterSpacing: '0.005em',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
      letterSpacing: '0.01em',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
  shape: {
    borderRadius: 8,
  },
})

export const createAppTheme = (mode: 'light' | 'dark') => {
  return createTheme(getDesignTokens(mode), ruRU)
}