import { CheckCircle2 } from 'lucide-react'
import { cn } from '../../app/components/ui/utils'

export type DocumentFlowStep = {
  key: string
  label: string
  description: string
}

export function DocumentFlowStepper({
  currentStep,
  steps,
}: {
  currentStep: number
  steps: DocumentFlowStep[]
}) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid gap-3 md:grid-cols-3">
        {steps.map((step, index) => {
          const active = index + 1 === currentStep
          const done = index + 1 < currentStep
          return (
            <div
              key={step.key}
              className={cn(
                'rounded-2xl border p-4 transition',
                done ? 'border-emerald-200 bg-emerald-50/80' : active ? 'border-cyan-200 bg-cyan-50/80' : 'border-slate-200 bg-slate-50'
              )}
            >
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold',
                    done ? 'bg-emerald-600 text-white' : active ? 'bg-cyan-600 text-white' : 'bg-slate-200 text-slate-600'
                  )}
                >
                  {done ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
                </div>
                <div>
                  <p className="font-semibold text-slate-900">{step.label}</p>
                  <p className="text-sm text-slate-600">{step.description}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
