'use client'

import { useEffect, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { api } from '../../../lib/api'
import { resetDemoClientData, seedDemoClientData } from '../../../lib/demo-bootstrap'

type PersonLite = { id: string; display_name: string; relationship: string; is_default?: boolean }

export default function DemoBootstrapPage() {
  const [persons, setPersons] = useState<PersonLite[]>([])
  const [status, setStatus] = useState('Ready')

  useEffect(() => {
    api
      .listPersons()
      .then((rows: PersonLite[]) => setPersons(rows))
      .catch(() => setStatus('請先登入 demo 帳號後再載入前端 demo 資料'))
  }, [])

  const onSeed = () => {
    seedDemoClientData(persons)
    setStatus('已寫入 demo actions + analytics（localStorage）')
  }

  const onReset = () => {
    resetDemoClientData(persons)
    setStatus('已清除 demo actions + analytics（localStorage）')
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-2xl font-semibold">Demo 啟動</h2>
        <p className="mt-1 text-sm text-slate-600">一鍵灌入前端展示資料（行動 / 分析）。</p>
        <p className="mt-1 text-xs text-slate-500">目前人物：{persons.map((p) => p.display_name).join(' / ') || '尚未載入'}</p>
      </Card>
      <Card className="flex flex-wrap items-center gap-2">
        <Button onClick={onSeed} className="bg-emerald-600 hover:bg-emerald-700">
          灌入 Demo 資料
        </Button>
        <Button onClick={onReset} className="bg-slate-600 hover:bg-slate-700">
          清除 Demo 資料
        </Button>
        <span className="text-sm text-slate-600">{status}</span>
      </Card>
    </div>
  )
}
