'use client'

import Link from 'next/link'
import { ReactNode, useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { Activity, ChevronDown, Moon, Sparkles, Sun } from 'lucide-react'
import { OnboardingWizard } from '../components/platform/onboarding-wizard'
import { NotificationBell } from '../components/platform/notification-bell'
import { PersonSwitcher } from '../components/platform/person-switcher'
import { DailyCheckinWidget } from '../components/platform/daily-checkin-widget'
import { ApiErrorToastProvider } from '../components/ui/api-error-toast'
import { ActionProvider } from '../providers/action-context'
import { PersonProvider } from '../providers/person-context'
import { trackEvent } from '../../lib/analytics'

// Primary nav: 4 most important items + orchestration
const PRIMARY_LINKS = [
  ['儀表板', '/platform/dashboard'],
  ['行動', '/platform/actions'],
  ['洞察', '/platform/insights'],
  ['報告', '/platform/documents'],
  ['AI 排程', '/platform/cockpit/orchestration'],
] as const

// Secondary links: accessible via "更多" dropdown
const MORE_LINKS = [
  ['時間軸', '/platform/timeline'],
  ['症狀', '/platform/symptoms'],
  ['家庭管理', '/platform/settings/family'],
  ['待處理中心', '/platform/notifications'],
  ['每週報告', '/platform/weekly-report'],
  ['分析', '/platform/analytics'],
  ['Demo 啟動', '/platform/demo-bootstrap'],
  ['AI 駕駛艙', '/platform/cockpit'],
  ['CTO 審核', '/platform/cockpit/cto-review'],
] as const

type PlatformLayoutProps = Readonly<{ children: ReactNode }>

export default function PlatformLayout({ children }: PlatformLayoutProps) {
  const pathname = usePathname()
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef<HTMLDivElement>(null)
  const shouldShowDailyCheckin = showOnboarding === false

  useEffect(() => {
    if (sessionStorage.getItem('analytics_opened')) return
    sessionStorage.setItem('analytics_opened', '1')
    trackEvent('user_open_app', { page: '/platform' })
  }, [])

  useEffect(() => {
    // Show onboarding once if never completed
    if (globalThis.window && !localStorage.getItem('onboarding_completed')) {
      setShowOnboarding(true)
    }
  }, [])

  useEffect(() => {
    const saved = localStorage.getItem('platform_theme')
    const next = saved === 'dark' ? 'dark' : 'light'
    setTheme(next)
    document.documentElement.dataset.theme = next
  }, [])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    localStorage.setItem('platform_theme', next)
    document.documentElement.dataset.theme = next
  }

  return (
    <PersonProvider>
      <ActionProvider>
        <ApiErrorToastProvider>
          {showOnboarding && <OnboardingWizard onComplete={() => setShowOnboarding(false)} />}
          <div className="mx-auto max-w-7xl px-4 pb-24 pt-6 sm:pb-6">
          <header className="glass-panel mb-6 rounded-2xl p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3 sm:flex-nowrap">
              <div className="flex items-center gap-2">
                <div className="rounded-xl bg-gradient-to-br from-sky-100 to-indigo-100 p-2 text-sky-700">
                  <Activity className="h-4 w-4" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">個人健康分析平台</h1>
                  <p className="text-xs text-slate-500">AI 輔助的健康決策支援</p>
                </div>
              </div>
              <nav className="flex w-full flex-wrap items-center gap-2 md:ml-4 md:w-auto">
                {PRIMARY_LINKS.map(([label, href]) => (
                  <Link
                    key={href}
                    href={href}
                    className={`rounded-xl border px-3 py-1.5 text-sm shadow-sm transition ${
                      pathname === href
                        ? 'border-sky-200 bg-sky-50 text-sky-700'
                        : 'border-transparent bg-white/90 text-slate-600 hover:border-slate-200 hover:text-slate-900'
                    }`}
                  >
                    {label}
                  </Link>
                ))}
                {/* 更多 dropdown */}
                <div ref={moreRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setMoreOpen((v) => !v)}
                    className={`flex items-center gap-1 rounded-xl border px-3 py-1.5 text-sm shadow-sm transition ${
                      MORE_LINKS.some(([, href]) => pathname === href)
                        ? 'border-sky-200 bg-sky-50 text-sky-700'
                        : 'border-transparent bg-white/90 text-slate-600 hover:border-slate-200 hover:text-slate-900'
                    }`}
                  >
                    更多 <ChevronDown className="h-3.5 w-3.5" />
                  </button>
                  {moreOpen && (
                    <div className="absolute left-0 top-full z-30 mt-1.5 w-40 rounded-2xl border border-slate-100 bg-white py-1.5 shadow-lg">
                      {MORE_LINKS.map(([label, href]) => (
                        <Link
                          key={href}
                          href={href}
                          onClick={() => setMoreOpen(false)}
                          className={`block px-4 py-2 text-sm transition ${
                            pathname === href ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-50'
                          }`}
                        >
                          {label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </nav>
              <div className="ml-auto flex items-center gap-1 sm:gap-2">
                <Link
                  href="/platform/login"
                  className="rounded-xl border border-transparent bg-white/90 px-3 py-1.5 text-sm text-slate-600 shadow-sm transition hover:border-slate-200 hover:text-slate-900"
                >
                  登入
                </Link>
                <NotificationBell />
                <button
                  onClick={toggleTheme}
                  className="glass-panel rounded-xl p-2 text-slate-600 shadow-sm transition hover:text-slate-900"
                  aria-label="Toggle theme"
                  type="button"
                >
                  {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </button>
                <Sparkles className="hidden h-4 w-4 text-slate-400 sm:block" />
                <span className="hidden text-sm text-slate-500 sm:inline">Person</span>
                <PersonSwitcher />
              </div>
            </div>
          </header>
          {children}
          {shouldShowDailyCheckin && <DailyCheckinWidget />}
          </div>
        </ApiErrorToastProvider>
      </ActionProvider>
    </PersonProvider>
  )
}
