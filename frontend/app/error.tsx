'use client'

import { useEffect } from 'react'
import { reportFrontendError } from '../lib/error-tracking'

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    reportFrontendError({
      message: error.message,
      stack: error.stack,
      context: { digest: error.digest },
    })
  }, [error])

  return (
    <html>
      <body className="p-6">
        <h2 className="text-xl font-semibold">Something went wrong</h2>
        <p className="mt-2 text-sm text-slate-600">An unexpected error occurred. Please retry.</p>
        <button
          className="mt-4 rounded bg-slate-900 px-4 py-2 text-white"
          onClick={() => reset()}
          type="button"
        >
          Try again
        </button>
      </body>
    </html>
  )
}
