// Type definitions for Botrix Dashboard

export interface Account {
  id: string
  email: string
  username: string
  password: string
  status: 'active' | 'failed' | 'banned'
  created_at: string
  updated_at: string
}

export interface Job {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  count: number
  progress: number
  successful: number
  failed: number
  created_at: string
  updated_at: string
  started_at?: string
  completed_at?: string
  error_msg?: string
  test_mode?: boolean
  priority?: number
}

export interface Stats {
  total_accounts: number
  active_accounts: number
  failed_accounts: number
  total_jobs: number
  active_jobs: number
  completed_jobs: number
  success_rate: number
  today_accounts: number
}

export interface WebSocketMessage {
  type: 'job_update' | 'account_created' | 'error'
  job_id?: string
  account_id?: string
  status?: string
  progress?: number
  data?: any
  message?: string
}

export interface CreateAccountRequest {
  count: number
}

export interface ApiResponse<T> {
  data: T
  message?: string
  error?: string
}

export interface PaginationParams {
  limit?: number
  offset?: number
}

export interface AccountsResponse {
  accounts: Account[]
  total: number
  limit: number
  offset: number
}

export interface JobsResponse {
  jobs: Job[]
  total: number
}
