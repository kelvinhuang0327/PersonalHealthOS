'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'
import { ChevronDown, UserPlus } from 'lucide-react'
import { usePerson } from '../../providers/person-context'
import { trackEvent } from '../../../lib/analytics'

const RELATIONSHIP_LABEL: Record<string, string> = {
  self: '本人',
  spouse: '配偶',
  child: '子女',
  parent: '父母',
}

export function PersonSwitcher() {
  const { persons, personId, currentPerson, setPersonId } = usePerson()
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  const initials = (currentPerson?.display_name || 'P').slice(0, 1).toUpperCase()

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-2 py-1.5"
      >
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-sky-100 text-xs font-semibold text-sky-700">{initials}</span>
        <span className="hidden text-sm text-slate-700 sm:inline">{currentPerson?.display_name || 'Person'}</span>
        <ChevronDown className="h-4 w-4 text-slate-400" />
      </button>

      {open ? (
        <div className="absolute right-0 top-full z-40 mt-2 w-64 rounded-2xl border bg-white p-2 shadow-xl">
          {persons.map((person) => {
            const selected = person.id === personId
            return (
              <button
                key={person.id}
                type="button"
                onClick={() => {
                  trackEvent('switch_person', { page: pathname || '/platform', metadata: { from: personId, to: person.id } })
                  setPersonId(person.id)
                  setOpen(false)
                  if (pathname) router.push(pathname)
                  router.refresh()
                }}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left ${selected ? 'bg-sky-50 text-sky-700' : 'hover:bg-slate-50'}`}
              >
                <span className="text-sm font-medium">{person.display_name}</span>
                <span className="text-xs text-slate-400">{RELATIONSHIP_LABEL[person.relationship] || person.relationship || '家人'}</span>
              </button>
            )
          })}
          <div className="my-1 border-t" />
          <Link
            href="/platform/settings/family"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            <UserPlus className="h-4 w-4" />
            新增家庭成員
          </Link>
        </div>
      ) : null}
    </div>
  )
}
