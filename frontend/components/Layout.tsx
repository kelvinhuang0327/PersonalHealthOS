import Link from 'next/link';
import { useRouter } from 'next/router';
import { ReactNode, useEffect, useMemo, useState } from 'react';
import { Activity, Bell, ChevronRight, FileUp, History, Home, LogOut, ShieldCheck, UserRound } from 'lucide-react';
import { ActionProvider, useActions } from '../app/providers/action-context';
import { PersonProvider, usePerson } from '../app/providers/person-context';
import { Badge } from '../app/components/ui/badge';
import { Button } from '../app/components/ui/button';
import { Card } from '../app/components/ui/card';
import { FlowBanner } from '../app/components/platform/flow-banner';
import { cn } from '../app/components/ui/utils';

const primaryLinks = [
  { href: '/dashboard', label: '首頁', description: '今日重點', icon: Home },
  { href: '/documents', label: '報告', description: '上傳與解析', icon: FileUp },
  { href: '/timeline', label: '時間軸', description: '時間軸與趨勢', icon: History },
  { href: '/actions', label: '行動', description: '提醒與任務', icon: Bell },
  { href: '/profile', label: 'Profile', description: '健康背景', icon: UserRound },
] as const;

const supportLinks = [
  { href: '/symptoms', label: '症狀自述' },
  { href: '/health-alerts', label: '風險警示' },
  { href: '/ai-summary', label: 'AI 摘要' },
] as const;

export function Layout({ children }: { children: ReactNode }) {
  return (
    <PersonProvider>
      <ActionProvider>
        <Shell>{children}</Shell>
      </ActionProvider>
    </PersonProvider>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { persons, personId, setPersonId } = usePerson();
  const { actions } = useActions();
  const [flash, setFlash] = useState<{ tone: 'success' | 'info' | 'warning'; title: string; message: string } | null>(null);

  const pendingActions = useMemo(
    () => actions.filter((action) => action.status === 'todo' || action.status === 'in_progress').length,
    [actions]
  );
  const riskUpActions = useMemo(
    () => actions.filter((action) => action.reminder_status === 'risk_up' || action.priority === 'high').length,
    [actions]
  );

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('person_id');
    router.push('/login');
  };

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('health_platform_flash');
      if (!raw) return;
      const parsed = JSON.parse(raw) as { tone?: 'success' | 'info' | 'warning'; title?: string; message?: string };
      if (parsed?.title && parsed?.message) {
        setFlash({
          tone: parsed.tone || 'info',
          title: parsed.title,
          message: parsed.message,
        });
      }
      sessionStorage.removeItem('health_platform_flash');
    } catch {
      sessionStorage.removeItem('health_platform_flash');
    }
  }, [router.pathname, personId]);

  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <div className="container">
        <header className="glass-panel mb-6 rounded-[28px] p-4 md:p-5">
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-gradient-to-br from-cyan-100 via-sky-100 to-emerald-100 p-3 text-cyan-800 shadow-sm">
                  <Activity className="h-5 w-5" />
                </div>
                <div>
                  <p className="section-label">個人健康平台</p>
                  <h1 className="font-['Figtree'] text-2xl font-semibold tracking-tight text-slate-900">可解釋的健康決策平台</h1>
                  <p className="mt-1 max-w-2xl text-sm text-slate-600">
                    先看狀態、再看變化、最後做下一步。每個 AI 洞察都必須能回到原始健康資料。
                  </p>
                </div>
              </div>

              <Card className="min-w-[280px] rounded-[24px] border-cyan-100 bg-gradient-to-br from-slate-900 via-slate-800 to-cyan-900 p-4 text-white shadow-none">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">今日</p>
                    <p className="mt-1 font-['Figtree'] text-2xl font-semibold">{pendingActions}</p>
                    <p className="text-sm text-cyan-100">待處理行動</p>
                  </div>
                  <Badge className={cn('border-none', riskUpActions > 0 ? 'bg-rose-400/20 text-rose-100' : 'bg-emerald-400/20 text-emerald-100')}>
                    {riskUpActions > 0 ? `${riskUpActions} 高優先提醒` : '目前無高風險任務'}
                  </Badge>
                </div>
                <p className="mt-3 text-xs leading-5 text-slate-200">
                    本平台提供健康資訊整理與追蹤建議，非醫療診斷或治療指示。
                </p>
              </Card>
            </div>

            <nav className="nav rounded-[24px] border border-white/60 bg-white/70 p-3 shadow-sm backdrop-blur-sm" aria-label="Primary">
              {primaryLinks.map((link) => {
                const Icon = link.icon;
                const active = router.pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      'group flex min-w-[148px] flex-1 items-center gap-3 rounded-2xl border px-4 py-3 transition',
                      active
                        ? 'border-cyan-200 bg-cyan-50 text-cyan-900'
                        : 'border-transparent bg-white/80 text-slate-600 hover:border-slate-200 hover:bg-white hover:text-slate-900'
                    )}
                  >
                    <div className={cn('rounded-xl p-2', active ? 'bg-cyan-100 text-cyan-700' : 'bg-slate-100 text-slate-500 group-hover:bg-slate-900 group-hover:text-white')}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold">{link.label}</div>
                      <div className="text-xs text-slate-500">{link.description}</div>
                    </div>
                  </Link>
                );
              })}
            </nav>

            <nav className="flex flex-wrap items-center gap-3" aria-label="Secondary">
              <div className="flex flex-wrap gap-2">
                {supportLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 transition hover:border-cyan-200 hover:text-cyan-900"
                  >
                    {link.label}
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Link>
                ))}
              </div>

              <div className="ml-auto flex flex-wrap items-center gap-2">
                <span className="text-sm text-slate-500">目前檢視對象</span>
                <select
                  value={personId}
                  onChange={(e) => {
                    const selected = persons.find((person) => person.id === e.target.value);
                    sessionStorage.setItem(
                      'health_platform_flash',
                      JSON.stringify({
                        tone: 'success',
                        title: '已切換檢視對象',
                        message: selected ? `現在正在查看 ${selected.display_name} 的健康資料。` : '已完成檢視對象切換。',
                      })
                    );
                    setPersonId(e.target.value);
                    router.reload();
                  }}
                  className="w-[220px]"
                >
                  {persons.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.display_name} ({person.relationship})
                    </option>
                  ))}
                </select>
                <Button
                  type="button"
                  className="bg-slate-900 hover:bg-slate-800"
                  onClick={() => router.push('/documents')}
                >
                  <FileUp className="mr-2 h-4 w-4" />
                  上傳報告
                </Button>
                  <button
                  type="button"
                  onClick={logout}
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
                >
                  <LogOut className="h-4 w-4" />
                  登出
                </button>
              </div>
            </nav>

            <div className="grid gap-3 md:grid-cols-3">
              <Card className="rounded-[22px] border-cyan-100 bg-cyan-50/80 p-4 shadow-none">
                <div className="flex items-center gap-2 text-cyan-800">
                  <ShieldCheck className="h-4 w-4" />
                  <p className="font-semibold">可解釋 AI</p>
                </div>
                <p className="mt-1 text-sm leading-6 text-cyan-900">
                  每則洞察都應顯示來源規則、證據等級、可信度與建議追蹤方向。
                </p>
              </Card>
              <Card className="rounded-[22px] border-amber-100 bg-amber-50/90 p-4 shadow-none">
                <p className="font-semibold text-amber-900">提醒策略</p>
                <p className="mt-1 text-sm leading-6 text-amber-900">
                  區分風險警示、待辦任務與一般洞察，避免把所有資訊都塞進同一個通知通道。
                </p>
              </Card>
              <Card className="rounded-[22px] border-emerald-100 bg-emerald-50/90 p-4 shadow-none">
                <p className="font-semibold text-emerald-900">資料寫入原則</p>
                <p className="mt-1 text-sm leading-6 text-emerald-900">
                  AI 解析出的健檢欄位必須先人工確認，再寫入長期健康資料與風險模型。
                </p>
              </Card>
            </div>
          </div>
        </header>

        {flash ? (
          <div className="mb-6">
            <FlowBanner tone={flash.tone} title={flash.title} message={flash.message} />
          </div>
        ) : null}

        <main id="main-content" key={personId}>
          {children}
        </main>
      </div>
    </>
  );
}
