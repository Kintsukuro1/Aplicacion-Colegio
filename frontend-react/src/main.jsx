import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';

import App from './App';
import { TenantProvider } from './utils/tenantContext';
import { queryClient } from './services/queryClient';
import { initMultiTabSync } from './stores/authStore';
import './styles.css';

// Initialize multi-tab token synchronization
const unsubscribeMultiTabSync = initMultiTabSync();

// Register Service Worker for PWA support
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .catch((error) => {
        // Silent fallback: PWA should never block the app shell
        console.debug('[PWA] SW registration failed:', error);
      });
  });
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TenantProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </TenantProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

// Cleanup multi-tab sync on app unload (if needed)
window.addEventListener('beforeunload', unsubscribeMultiTabSync);

