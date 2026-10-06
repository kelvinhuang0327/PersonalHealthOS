'use client'

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../../lib/api'

type Person = { id: string; display_name: string; relationship: string; is_default?: boolean }

type PersonContextValue = {
  persons: Person[]
  personId: string
  currentPerson: Person | null
  setPersonId: (id: string) => void
  refreshPersons: () => Promise<void>
}

const PersonContext = createContext<PersonContextValue>({
  persons: [],
  personId: '',
  currentPerson: null,
  setPersonId: () => {},
  refreshPersons: async () => {},
})

export function PersonProvider({ children }: { children: ReactNode }) {
  const [persons, setPersons] = useState<Person[]>([])
  const [personId, setPersonIdState] = useState('')

  const refreshPersons = useCallback(async () => {
    api.listPersons().then((rows: Person[]) => {
      setPersons(rows)
      const localPerson = localStorage.getItem('person_id')
      const resolved = localPerson || rows.find((r) => r.is_default)?.id || rows[0]?.id || ''
      if (resolved) {
        localStorage.setItem('person_id', resolved)
        setPersonIdState(resolved)
      }
    }).catch(() => setPersons([]))
  }, [])

  useEffect(() => {
    void refreshPersons()
  }, [])

  const value = useMemo(() => ({
    persons,
    personId,
    currentPerson: persons.find((person) => person.id === personId) || null,
    setPersonId: (id: string) => {
      localStorage.setItem('person_id', id)
      setPersonIdState(id)
    },
    refreshPersons,
  }), [persons, personId, refreshPersons])

  return <PersonContext.Provider value={value}>{children}</PersonContext.Provider>
}

export function usePerson() {
  return useContext(PersonContext)
}
