import axios, { AxiosError } from 'axios';
import type {
  Account,
  Job,
  Stats,
  CreateAccountRequest,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

// Enhanced API Error class for better error handling
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  validateStatus: (status) => status >= 200 && status < 500, // Don't throw on 4xx errors
});

// Request interceptor for logging and debugging
apiClient.interceptors.request.use(
  (config) => {
    const timestamp = new Date().toISOString();
    console.log(`[API ${timestamp}] → ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    
    if (config.data) {
      console.log(`[API ${timestamp}] Request Body:`, config.data);
    }
    
    return config;
  },
  (error) => {
    console.error('[API] Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and logging
apiClient.interceptors.response.use(
  (response) => {
    const timestamp = new Date().toISOString();
    console.log(`[API ${timestamp}] ← ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
    console.log(`[API ${timestamp}] Response:`, response.data);
    
    // Handle backend error responses with success: false
    if (response.data && response.data.success === false) {
      const errorMessage = response.data.error || response.data.message || 'Unknown error';
      throw new ApiError(errorMessage, response.status, response.data);
    }
    
    return response;
  },
  (error: AxiosError) => {
    const timestamp = new Date().toISOString();
    
    if (error.response) {
      // Server responded with error status
      const errorData = error.response.data as any;
      const message = errorData?.error || errorData?.message || error.message || 'Server error';
      
      console.error(`[API ${timestamp}] ✗ ${error.response.status} ${error.config?.method?.toUpperCase()} ${error.config?.url}`);
      console.error(`[API ${timestamp}] Error:`, message);
      console.error(`[API ${timestamp}] Error Data:`, errorData);
      
      throw new ApiError(message, error.response.status, errorData);
    } else if (error.request) {
      // Request made but no response received
      console.error(`[API ${timestamp}] ✗ No response from server`);
      console.error(`[API ${timestamp}] Request:`, error.request);
      throw new ApiError('No response from server. Please check your connection.', 0);
    } else {
      // Error setting up request
      console.error(`[API ${timestamp}] ✗ Request setup error:`, error.message);
      throw new ApiError(error.message);
    }
  }
);

// API methods with enhanced error handling and type safety
export const api = {
  // Accounts
  accounts: {
    list: async (): Promise<Account[]> => {
      try {
        const response = await apiClient.get<{ success: boolean; data: Account[] }>('/api/accounts');
        
        if (!response.data.success) {
          throw new ApiError('Failed to fetch accounts');
        }
        
        return response.data.data || [];
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Failed to fetch accounts list', 0, error);
      }
    },
    
    get: async (id: number): Promise<Account> => {
      try {
        const response = await apiClient.get<{ success: boolean; account: Account }>(`/api/accounts/${id}`);
        
        if (!response.data.success || !response.data.account) {
          throw new ApiError('Account not found', 404);
        }
        
        return response.data.account;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(`Failed to fetch account ${id}`, 0, error);
      }
    },
    
    create: async (data: CreateAccountRequest): Promise<Job> => {
      try {
        const response = await apiClient.post<{ success: boolean; job: Job; message?: string }>('/api/accounts', data);
        
        if (!response.data.success || !response.data.job) {
          throw new ApiError(response.data.message || 'Failed to create account');
        }
        
        return response.data.job;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Failed to create account', 0, error);
      }
    },
    
    update: async (id: number, data: Partial<Account>): Promise<Account> => {
      try {
        const response = await apiClient.put<{ success: boolean; account: Account; message?: string }>(`/api/accounts/${id}`, data);
        
        if (!response.data.success || !response.data.account) {
          throw new ApiError(response.data.message || 'Failed to update account');
        }
        
        return response.data.account;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(`Failed to update account ${id}`, 0, error);
      }
    },
    
    delete: async (id: number): Promise<void> => {
      try {
        const response = await apiClient.delete<{ success: boolean; message?: string }>(`/api/accounts/${id}`);
        
        if (!response.data.success) {
          throw new ApiError(response.data.message || 'Failed to delete account');
        }
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(`Failed to delete account ${id}`, 0, error);
      }
    },
  },

  // Jobs
  jobs: {
    list: async (): Promise<Job[]> => {
      try {
        const response = await apiClient.get<{ success: boolean; jobs: Job[] }>('/api/jobs');
        
        if (!response.data.success) {
          throw new ApiError('Failed to fetch jobs');
        }
        
        return response.data.jobs || [];
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Failed to fetch jobs list', 0, error);
      }
    },
    
    get: async (id: string): Promise<Job> => {
      try {
        const response = await apiClient.get<{ success: boolean; job: Job }>(`/api/jobs/${id}`);
        
        if (!response.data.success || !response.data.job) {
          throw new ApiError('Job not found', 404);
        }
        
        return response.data.job;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(`Failed to fetch job ${id}`, 0, error);
      }
    },
    
    cancel: async (id: string): Promise<void> => {
      try {
        const response = await apiClient.post<{ success: boolean; message?: string }>(`/api/jobs/${id}/cancel`);
        
        if (!response.data.success) {
          throw new ApiError(response.data.message || 'Failed to cancel job');
        }
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError(`Failed to cancel job ${id}`, 0, error);
      }
    },
    
    stats: async (): Promise<Stats> => {
      try {
        const response = await apiClient.get<Stats>('/api/jobs/stats');
        
        if (!response.data.success) {
          throw new ApiError('Failed to fetch job stats');
        }
        
        return response.data;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Failed to fetch job statistics', 0, error);
      }
    },
    
    generate: async (count: number): Promise<{ job_ids: string[]; message: string }> => {
      try {
        const response = await apiClient.post<{ success: boolean; job_ids: string[]; message?: string }>('/api/accounts/generate', {
          count,
          priority: 'normal',
        });
        
        if (!response.data.success) {
          throw new ApiError(response.data.message || 'Failed to generate accounts');
        }
        
        return {
          job_ids: response.data.job_ids || [],
          message: response.data.message || 'Jobs created successfully',
        };
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Failed to generate accounts', 0, error);
      }
    },
  },

  // Health
  health: {
    check: async () => {
      try {
        const response = await apiClient.get('/health');
        return response.data;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Health check failed', 0, error);
      }
    },
    
    ping: async () => {
      try {
        const response = await apiClient.get('/health/ping');
        return response.data;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Ping failed', 0, error);
      }
    },
  },

  // Stats
  stats: {
    get: async (): Promise<Stats> => {
      try {
        const response = await apiClient.get<Stats>('/api/stats');
        
        if (!response.data.success) {
          throw new ApiError('Failed to fetch statistics');
        }
        
        return response.data;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        throw new ApiError('Failed to fetch statistics', 0, error);
      }
    },
  },
};

export default apiClient;
