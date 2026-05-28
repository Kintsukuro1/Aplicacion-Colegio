import { useState } from 'react';
import { useToast } from '@/components/feedback/Toast';
import { apiClient } from '@/services/apiClient';

/**
 * useFormCRUD - Unified form state + CRUD operations (create, read, update, delete)
 * 
 * Reduces boilerplate for pages with form-based CRUD workflows.
 * Manages: form state, editing mode, loading, errors, and CRUD operations.
 * 
 * @param {Object} config
 * @param {Object} config.initialForm - Default form state { title: '', description: '' }
 * @param {string} config.endpoint - API endpoint for CRUD ops: /api/v1/resource/
 * @param {Function} config.onSuccess - Called after successful create/update/delete
 * @param {Object} config.defaults - Additional defaults to merge into form
 * 
 * @returns {Object} { form, setForm, editingId, startEdit, resetForm, loading, saving,
 *                     create, update, delete: deleteRecord, error, clearError }
 */
export function useFormCRUD({
  initialForm = {},
  endpoint = '',
  onSuccess = () => {},
  defaults = {},
  getId = null,
  mapRecordToForm = null,
  mapFormToPayload = null,
}) {
  const toast = useToast();
  const [form, setForm] = useState({ ...initialForm, ...defaults });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const resolveId = getId || ((record) => record?.id);
  const toForm = mapRecordToForm || ((record) => record || {});
  const toPayload = mapFormToPayload || ((payload) => payload);

  const resetForm = () => {
    setForm({ ...initialForm, ...defaults });
    setEditingId(null);
    setError(null);
  };

  const startEdit = (record) => {
    setForm(toForm(record));
    setEditingId(resolveId(record));
    setError(null);
  };

  const create = async (customData = null) => {
    setSaving(true);
    setError(null);
    try {
      const payload = customData || form;
      const response = await apiClient.post(endpoint, toPayload(payload));
      toast.success('Creado exitosamente');
      resetForm();
      onSuccess(response.data);
      return response.data;
    } catch (err) {
      const msg = err.payload?.detail || err.message || 'Error al crear';
      setError(msg);
      toast.error(msg);
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const update = async (customData = null) => {
    if (!editingId) {
      setError('No record selected for update');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = customData || form;
      const response = await apiClient.patch(`${endpoint}${editingId}/`, toPayload(payload));
      toast.success('Actualizado exitosamente');
      resetForm();
      onSuccess(response.data);
      return response.data;
    } catch (err) {
      const msg = err.payload?.detail || err.message || 'Error al actualizar';
      setError(msg);
      toast.error(msg);
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const deleteRecord = async (recordId = editingId) => {
    if (!recordId) {
      setError('No record selected for deletion');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiClient.del(`${endpoint}${recordId}/`);
      toast.success('Eliminado exitosamente');
      resetForm();
      onSuccess({ id: recordId, deleted: true });
      return true;
    } catch (err) {
      const msg = err.payload?.detail || err.message || 'Error al eliminar';
      setError(msg);
      toast.error(msg);
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const clearError = () => setError(null);

  return {
    form,
    setForm,
    editingId,
    startEdit,
    resetForm,
    loading,
    saving,
    create,
    update,
    delete: deleteRecord,
    error,
    clearError,
  };
}
