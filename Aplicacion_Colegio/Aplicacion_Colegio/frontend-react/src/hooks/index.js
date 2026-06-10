/**
 * Central exports para custom hooks reutilizables
 */

// Legacy hooks (mantener para compatibilidad)
export { useFetch } from './useFetch';
export { usePagination } from './usePagination';
export { useAsync } from './useAsync';

// React Query hooks (Fase 4 - Data Fetching PRO)
export {
  useTasks,
  useTask,
  useSubmitTask,
  useUpdateTaskStatus,
} from './useTasks';

export {
  useMaterials,
  useMaterial,
  useDownloadMaterial,
  useCreateMaterial,
  useDeleteMaterial,
} from './useMaterials';

export {
  useMessages,
  useConversation,
  useSendMessage,
  useMarkMessagesAsRead,
  useCreateConversation,
  useDeleteMessage,
} from './useMessages';

// Fase 7 - CRUD & Refactoring Hooks
export { useFormCRUD } from './useFormCRUD';
export { usePermissionChecks } from './usePermissionChecks';
export { useBulkDeactivate } from './useBulkDeactivate';
export { useEventFilters } from './useEventFilters';

// SEO Hook (Fase 6)
export { usePageMeta, setPageMeta } from './usePageMeta';
