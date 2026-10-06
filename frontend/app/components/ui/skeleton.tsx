import { cn } from './utils'

export function Skeleton({ className, variant = 'text' }: { className?: string; variant?: 'text' | 'card' | 'chart' | 'avatar' }) {
  const variantClass =
    variant === 'card'
      ? 'rounded-2xl h-32'
      : variant === 'chart'
      ? 'rounded-2xl h-28'
      : variant === 'avatar'
      ? 'rounded-full h-10 w-10'
      : 'rounded h-4'

  return <div className={cn('animate-pulse bg-slate-200/80', variantClass, className)} aria-hidden="true" />
}
