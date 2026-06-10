import { useState } from 'react';
import { useToast } from '@/components/feedback/Toast';
import { apiClient } from '@/services/apiClient';

/**
 * useBulkDeactivate - Handle bulk deactivation with fallback to individual deletes
 * 
 * If bulk endpoint fails or is unavailable, automatically falls back to deleting
 * records one by one, tracking which succeeded/failed.
 * 
 * @param {Object} config
 * @param {string} config.bulkEndpoint - Batch API endpoint: /api/v1/resource/bulk-deactivate/
 * @param {string} config.singleEndpoint - Single delete endpoint: /api/v1/resource/{id}/
 * @param {Function} config.onSuccess - Called after operation completes
 * 
 * @returns {Object} { deactivate, saving, bulkResult, retry, clearResult }
 */
export function useBulkDeactivate({
  bulkEndpoint = '',
  singleEndpoint = '',
  onSuccess = () => {},
} = {}) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  const deactivate = async (ids) => {
    if (!ids || ids.length === 0) {
      toast.warning('No items selected');
      return;
    }

    setSaving(true);
    try {
      // Try bulk endpoint first
      const response = await apiClient.post(bulkEndpoint, { ids });
      toast.success(`${ids.length} registros desactivados`);
      onSuccess({ method: 'bulk', count: ids.length, details: response.data });
      return response.data;
    } catch (bulkError) {
      // Fallback: delete one by one
      console.warn('Bulk delete failed, falling back to individual deletes:', bulkError);
      
      const results = [];
      for (const id of ids) {
        try {
          await apiClient.del(`${singleEndpoint}${id}/`);
          results.push({ id, success: true });
        } catch (singleError) {
          results.push({ id, success: false, error: singleError.message });
        }
      }

      const successCount = results.filter((r) => r.success).length;
      const failCount = results.filter((r) => !r.success).length;

      setBulkResult({ successCount, failCount, details: results });

      if (failCount > 0) {
        toast.warning(`${successCount} eliminados, ${failCount} fallaron. Puedes reintentar.`);
      } else {
        toast.success(`${successCount} registros desactivados (uno por uno)`);
        onSuccess({ method: 'fallback', count: successCount, details: results });
      }

      return { method: 'fallback', results };
    } finally {
      setSaving(false);
    }
  };

  const retry = async (failedIds) => {
    return deactivate(failedIds);
  };

  const clearResult = () => {
    setBulkResult(null);
  };

  return {
    deactivate,
    saving,
    bulkResult,
    retry,
    clearResult,
  };
}
