import axios from 'axios';
import type {
  Account,
  Job,
  Stats,
  CreateAccountRequest,
  AccountsResponse,
  JobsResponse,
  PaginationParams,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message;
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  // Accounts
  accounts: {
    list: async (): Promise<Account[]> => {
      const response = await apiClient.get<Account[]>('/api/accounts');
      return response.data;
    },
    get: async (id: string): Promise<Account> => {
      const response = await apiClient.get<Account>(`/api/accounts/${id}`);
      return response.data;
    },
    create: async (data: CreateAccountRequest): Promise<Job> => {
      const response = await apiClient.post<Job>('/api/accounts', data);
      return response.data;
    },
    update: async (id: string, data: Partial<Account>): Promise<Account> => {
      const response = await apiClient.put<Account>(`/api/accounts/${id}`, data);
      return response.data;
    },
    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`/api/accounts/${id}`);
    },
    stats: async (): Promise<Stats> => {
      const response = await apiClient.get<Stats>('/api/accounts/stats');
      return response.data;
    },
  },

  // Jobs
  jobs: {
    list: async (): Promise<Job[]> => {
      const response = await apiClient.get<{ success: boolean; jobs: Job[] }>('/api/jobs');
      return response.data.jobs || [];
    },
    get: async (id: string): Promise<Job> => {
      const response = await apiClient.get<{ success: boolean; job: Job }>(`/api/jobs/${id}`);
      return response.data.job;
    },
    cancel: async (id: string): Promise<void> => {
      await apiClient.post(`/api/jobs/${id}/cancel`);
    },
    stats: async (): Promise<Stats> => {
      const response = await apiClient.get<Stats>('/api/jobs/stats');
      return response.data;
    },
    generate: async (count: number, test?: boolean): Promise<Job> => {
      const response = await apiClient.post<{ success: boolean; job: Job; message?: string }>('/api/accounts/generate', {
        count,
        test_mode: test || false,
      });
      return response.data.job;
    },
  },

  // Health
  health: {
    check: async () => {
      const response = await apiClient.get('/health');
      return response.data;
    },
    ping: async () => {
      const response = await apiClient.get('/ping');
      return response.data;
    },
  },
};

export default apiClient;
