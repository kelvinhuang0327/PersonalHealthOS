'use client'

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { personsApi as api } from '../../lib/persons-client'
import type { PersonRecord } from '../../lib/persons-client'

type PersonContextValue = {
  persons: Person[]
  personId: string
  currentPerson: Person | null
  setPersonId: (id: string) => void
  refreshPersons: () => Promise<void>
}

type Person = PersonRecord

function isPersonRecord(person: unknown): person is PersonRecord {
  if (
    typeof person !== 'object' ||
    person === null ||
    !('id' in person) ||
    !('display_name' in person)
  ) {
    return false
  }

  return (
    typeof person.id === 'string' &&
    person.id.trim().length > 0 &&
    typeof person.display_name === 'string' &&
    person.display_name.trim().length > 0
  )
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
    api.listPersons().then((rows) => {
      // relationship and relationship_type are optional; selectable identity depends on id and display_name.
      const validPersons = rows.filter(isPersonRecord)
      setPersons(validPersons)
      const localPerson = localStorage.getItem('person_id')
      const resolved = localPerson || validPersons.find((r) => r.is_default)?.id || validPersons[0]?.id || ''
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
