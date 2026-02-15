/**
 * Authentication Store (Zustand)
 */

import { create } from 'zustand';
import { authApi } from '@/api/auth';
import { User, LoginCredentials, RegisterData } from '@/types/auth';
import { handleApiError } from '@/api/client';

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authApi.login(credentials);
      set({
        user: response.data.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      const apiError = handleApiError(error);
      set({
        error: apiError.error.message,
        isLoading: false,
        isAuthenticated: false,
      });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authApi.register(data);
      set({
        user: response.data.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      const apiError = handleApiError(error);
      set({
        error: apiError.error.message,
        isLoading: false,
        isAuthenticated: false,
      });
      throw error;
    }
  },

  logout: async () => {
    set({ isLoading: true });

    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  },

  loadUser: async () => {
    set({ isLoading: true });

    try {
      const response = await authApi.getCurrentUser();
      set({
        user: response.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
