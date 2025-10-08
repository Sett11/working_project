declare module 'react-world-flags' {
  import { CSSProperties } from 'react'

  interface FlagProps {
    code: string
    style?: CSSProperties
    className?: string
    fallback?: React.ReactNode
    height?: string | number
    width?: string | number
  }

  const Flag: React.FC<FlagProps>
  export default Flag
}

