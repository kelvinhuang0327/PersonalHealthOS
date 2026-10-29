import { QuickCheckInPanel } from '../../components/platform/quick-check-in-panel'

export default function QuickCheckInPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 pb-8 pt-6">
      <div className="space-y-4">
        <header className="space-y-2">
          <h2 className="text-2xl font-semibold text-slate-950">快速健康打卡</h2>
          <p className="text-sm text-slate-600">用幾個簡單選擇記下今天的狀況。</p>
        </header>
        <QuickCheckInPanel />
      </div>
    </main>
  )
}
