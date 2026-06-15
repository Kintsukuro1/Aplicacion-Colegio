import { create } from 'zustand';

let nextId = 0;
const isTestEnvironment = typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test';

export const useNotificationStore = create((set, get) => ({
  toasts: [],

  add: (message, type = 'info', duration = 4000) => {
    const id = ++nextId;
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }));

    if (!isTestEnvironment && duration > 0) {
      setTimeout(() => {
        get().dismiss(id);
      }, duration);
    }
  },

  dismiss: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  success: (msg, ms) => get().add(msg, 'success', ms),
  error: (msg, ms) => get().add(msg, 'error', ms ?? 6000),
  info: (msg, ms) => get().add(msg, 'info', ms),
  warning: (msg, ms) => get().add(msg, 'warning', ms ?? 5000),
}));
