import '@mui/material/styles'

/**
 * Расширение палитры MUI для добавления кастомных цветов бренда
 */
declare module '@mui/material/styles' {
  interface Palette {
    brand: {
      teal50: string
    }
  }

  interface PaletteOptions {
    brand?: {
      teal50?: string
    }
  }
}

