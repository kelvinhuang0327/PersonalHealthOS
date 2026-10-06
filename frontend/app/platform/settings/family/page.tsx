'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Button } from '../../../components/ui/button'
import { Card } from '../../../components/ui/card'
import { api, getLatestMetricByPerson } from '../../../../lib/api'
import { usePerson } from '../../../providers/person-context'

type Person = {
  id: string
  display_name: string
  relationship: string
  birth_date?: string | null
}

const REL_OPTIONS = [
  { value: 'self', label: '本人' },
  { value: 'spouse', label: '配偶' },
  { value: 'child', label: '子女' },
  { value: 'parent', label: '父母' },
]

export default function FamilySettingsPage() {
  const { refreshPersons } = usePerson()
  const [persons, setPersons] = useState<Person[]>([])
  const [latestMap, setLatestMap] = useState<Record<string, string>>({})
  const [editingId, setEditingId] = useState<string | null>(null)
  const [nameDraft, setNameDraft] = useState('')
  const [relDraft, setRelDraft] = useState('family')
  const [dobDraft, setDobDraft] = useState('')

  const [newName, setNewName] = useState('')
  const [newRel, setNewRel] = useState('child')
  const [newDob, setNewDob] = useState('')

  const load = async () => {
    const rows = (await api.listPersons().catch(() => [])) as Person[]
    setPersons(rows)
    const entries = await Promise.all(
      rows.map(async (person) => {
        const latest = await getLatestMetricByPerson(person.id)
        return [person.id, latest?.recorded_at ? new Date(latest.recorded_at).toLocaleDateString('zh-TW') : '尚未記錄'] as const
      })
    )
    setLatestMap(Object.fromEntries(entries))
  }

  useEffect(() => {
    void load()
  }, [])

  const startEdit = (person: Person) => {
    setEditingId(person.id)
    setNameDraft(person.display_name)
    setRelDraft(person.relationship)
    setDobDraft(person.birth_date ? String(person.birth_date) : '')
  }

  const saveEdit = async () => {
    if (!editingId) return
    await api.updatePerson(editingId, {
      display_name: nameDraft,
      relationship: relDraft,
      birth_date: dobDraft || undefined,
    })
    setEditingId(null)
    await refreshPersons()
    await load()
  }

  const onDelete = async (person: Person) => {
    const ok = window.confirm('刪除後，該成員所有健康資料將一併刪除')
    if (!ok) return
    await api.deletePerson(person.id)
    await refreshPersons()
    await load()
  }

  const onAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    await api.createPerson({
      display_name: newName.trim(),
      relationship: newRel,
      birth_date: newDob || undefined,
    })
    setNewName('')
    setNewRel('child')
    setNewDob('')
    await refreshPersons()
    await load()
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-2xl font-semibold">家庭成員管理</h2>
        <p className="mt-1 text-sm text-slate-500">管理家庭成員、關係與快速健康檢視。</p>
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">成員列表</h3>
        <div className="space-y-2">
          {persons.map((person) => {
            const editing = editingId === person.id
            return (
              <div key={person.id} className="rounded-xl border p-3">
                {editing ? (
                  <div className="grid gap-2 sm:grid-cols-4">
                    <input className="rounded border px-2 py-1.5" value={nameDraft} onChange={(e) => setNameDraft(e.target.value)} />
                    <select className="rounded border px-2 py-1.5" value={relDraft} onChange={(e) => setRelDraft(e.target.value)}>
                      {REL_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                    </select>
                    <input type="date" className="rounded border px-2 py-1.5" value={dobDraft} onChange={(e) => setDobDraft(e.target.value)} />
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => void saveEdit()}>儲存</Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>取消</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{person.display_name}</p>
                      <p className="text-xs text-slate-500">{REL_OPTIONS.find((r) => r.value === person.relationship)?.label || person.relationship} · 最近量測：{latestMap[person.id] || '尚未記錄'}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => startEdit(person)}>編輯</Button>
                      {person.relationship !== 'self' ? <Button size="sm" variant="destructive" onClick={() => void onDelete(person)}>刪除</Button> : null}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">新增家庭成員</h3>
        <form onSubmit={(e) => void onAdd(e)} className="grid gap-2 sm:grid-cols-4">
          <input className="rounded border px-2 py-1.5" placeholder="姓名" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <select className="rounded border px-2 py-1.5" value={newRel} onChange={(e) => setNewRel(e.target.value)}>
            {REL_OPTIONS.filter((opt) => opt.value !== 'self').map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <input type="date" className="rounded border px-2 py-1.5" value={newDob} onChange={(e) => setNewDob(e.target.value)} />
          <Button type="submit">新增</Button>
        </form>
      </Card>
    </div>
  )
}
