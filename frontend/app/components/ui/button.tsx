import { ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from './utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-60',
  {
    variants: {
      variant: {
        default:     'rounded-2xl bg-cyan-700 text-white shadow-sm hover:bg-cyan-800 hover:shadow-md',
        destructive: 'rounded-2xl bg-rose-600 text-white shadow-sm hover:bg-rose-700',
        outline:     'rounded-2xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
        ghost:       'rounded-xl text-slate-700 hover:bg-slate-100',
        link:        'text-sky-600 underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 text-sm',
        sm:      'h-8  px-3 text-sm',
        lg:      'h-11 px-6 text-base',
        icon:    'h-9  w-9  p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size:    'default',
    },
  },
)

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}
