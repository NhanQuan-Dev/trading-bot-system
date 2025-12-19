import apiClient from './client';

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
  timezone?: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  timezone: string;
  is_active: boolean;
  preferences: Record<string, unknown>;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse extends User {
  preferences: Record<string, unknown>;
}

export const authApi = {
  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/register', data);
    return response.data;
  },

  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/login', data);
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<RefreshResponse> => {
    const response = await apiClient.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await apiClient.get('/api/v1/users/me');
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};
