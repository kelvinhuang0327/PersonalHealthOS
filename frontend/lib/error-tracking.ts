type ErrorPayload = {
  message: string
  stack?: string
  context?: Record<string, unknown>
}

const errorTrackingDsn = process.env.NEXT_PUBLIC_ERROR_TRACKING_DSN

export function reportFrontendError(payload: ErrorPayload) {
  if (!errorTrackingDsn) {
    console.error('[frontend-error]', payload)
    return
  }
  console.error('[frontend-error][dsn-configured]', payload)
}
