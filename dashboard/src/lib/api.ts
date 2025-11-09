import axios from 'axios'
import type {
  Account,
  Job,
  Stats,
  CreateAccountRequest,
  AccountsResponse,
  JobsResponse,
  PaginationParams,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message
    console.error('API Error:', message)
    return Promise.reject(error)
  }
)

// Health Check
export const health = {
  check: () => api.get('/health'),
  ping: () => api.get('/ping'),
}

// Accounts API
export const accounts = {
  list: (params?: PaginationParams) =>
    api.get<AccountsResponse>('/api/accounts', { params }),
  get: (id: string) => api.get<Account>(`/api/accounts/${id}`),
  create: (data: CreateAccountRequest) => api.post<Job>('/api/accounts', data),
  update: (id: string, data: Partial<Account>) =>
    api.put<Account>(`/api/accounts/${id}`, data),
  delete: (id: string) => api.delete(`/api/accounts/${id}`),
  stats: () => api.get<Stats>('/api/accounts/stats'),
}

// Jobs API
export const jobs = {
  list: () => api.get<JobsResponse>('/api/jobs'),
  get: (id: string) => api.get<Job>(`/api/jobs/${id}`),
  cancel: (id: string) => api.post(`/api/jobs/${id}/cancel`),
  stats: () => api.get<Stats>('/api/jobs/stats'),
}

export default api
