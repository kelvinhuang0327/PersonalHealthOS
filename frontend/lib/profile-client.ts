import { apiRequest, jsonBody } from './http-client'

export type OnboardingProfileInput = {
  display_name?: string
  biological_sex?: string
  age?: number
}

export const profileApi = {
  updateProfile: async ({ display_name, biological_sex }: OnboardingProfileInput) => {
    const current = await apiRequest<{
      full_name: string | null
      birth_date: string | null
      gender: string | null
      height_cm: number | null
      weight_kg: number | null
      allergies: string | null
      family_history: string | null
      chronic_conditions: string | null
    }>('/profile/me', {}, { personScoped: true })

    // The backend PUT replaces nullable profile fields, so carry them forward.
    // ProfileUpsertRequest has no age field; do not invent a birth date from age.
    return apiRequest('/profile/me', {
      method: 'PUT',
      body: jsonBody({
        full_name: display_name ?? current.full_name,
        birth_date: current.birth_date,
        gender: biological_sex ?? current.gender,
        height_cm: current.height_cm,
        weight_kg: current.weight_kg,
        allergies: current.allergies,
        family_history: current.family_history,
        chronic_conditions: current.chronic_conditions,
      }),
    }, { personScoped: true })
  },
}
