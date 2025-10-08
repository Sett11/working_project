declare module 'react-world-flags' {
  interface FlagProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
    code?: string
    fallback?: React.ReactNode
  }

  const Flag: React.FC<FlagProps>
  export default Flag
}

