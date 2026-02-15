/**
 * Authentication API
 */

import apiClient, { ApiResponse, tokenManager } from './client';
import { User, LoginCredentials, RegisterData } from '@/types/auth';

export const authApi = {
  /**
   * Login user
   */
  async login(credentials: LoginCredentials): Promise<ApiResponse<{
    access: string;
    refresh: string;
    user: User;
  }>> {
    const response = await apiClient.post('/auth/login/', credentials);
    const { access, refresh } = response.data.data;

    // Store tokens
    await tokenManager.setTokens(access, refresh);

    return response.data;
  },

  /**
   * Register new user
   */
  async register(data: RegisterData): Promise<ApiResponse<{
    access: string;
    refresh: string;
    user: User;
  }>> {
    const response = await apiClient.post('/auth/register/', data);
    const { access, refresh } = response.data.data;

    // Store tokens
    await tokenManager.setTokens(access, refresh);

    return response.data;
  },

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      const refreshToken = await tokenManager.getRefreshToken();
      if (refreshToken) {
        await apiClient.post('/auth/logout/', { refresh: refreshToken });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear tokens regardless of API response
      await tokenManager.clearTokens();
    }
  },

  /**
   * Get current user
   */
  async getCurrentUser(): Promise<ApiResponse<User>> {
    const response = await apiClient.get('/auth/me/');
    return response.data;
  },

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<{ access: string; refresh: string }> {
    const refreshToken = await tokenManager.getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await apiClient.post('/auth/refresh/', {
      refresh: refreshToken,
    });

    const { access, refresh } = response.data;
    await tokenManager.setTokens(access, refresh);

    return { access, refresh };
  },
};
