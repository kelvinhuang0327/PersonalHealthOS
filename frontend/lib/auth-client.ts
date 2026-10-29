import { apiRequest, jsonBody } from './http-client'

export type AccessTokenResponse = { access_token: string; token_type?: string }

export const authApi = {
  login: (email: string, password: string) =>
    apiRequest<AccessTokenResponse>('/auth/login', {
      method: 'POST',
      body: jsonBody({ email, password }),
    }),
  register: (email: string, password: string) =>
    apiRequest<{ id: string; email: string }>('/auth/register', {
      method: 'POST',
      body: jsonBody({ email, password }),
    }),
}
