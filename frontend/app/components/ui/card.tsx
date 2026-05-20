import { HTMLAttributes, ReactNode } from 'react'
import { cn } from './utils'

export function Card({
  className,
  children,
  ...props
}: { className?: string; children: ReactNode } & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={cn(
        'glass-panel rounded-2xl shadow-sm p-4 transition hover:shadow-md',
        className,
      )}
    >
      {children}
    </div>
  )
}
