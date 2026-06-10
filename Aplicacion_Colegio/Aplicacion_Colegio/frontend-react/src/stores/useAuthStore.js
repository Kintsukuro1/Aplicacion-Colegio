import { create } from 'zustand';
import { clearTokens as clearLocalTokens, setTokens as setLocalTokens } from '@/stores/authStore';
import { queryClient } from '@/services/queryClient';

export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,

  setUser: (userData) => {
    set({
      user: userData,
      isAuthenticated: Boolean(userData),
    });
  },

  login: (tokens) => {
    setLocalTokens(tokens);
  },

  logout: () => {
    clearLocalTokens();
    queryClient.clear();
    set({
      user: null,
      isAuthenticated: false,
    });
  },
}));
