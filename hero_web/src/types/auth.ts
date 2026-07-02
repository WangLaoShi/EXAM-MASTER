export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
  confirm_password: string
}
