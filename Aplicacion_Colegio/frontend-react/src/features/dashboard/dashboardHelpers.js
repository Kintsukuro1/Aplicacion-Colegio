import { apiClient } from '../../services/apiClient';

export const EXECUTIVE_SCOPES = new Set(['school', 'analytics', 'global']);
const NUMBER_FORMATTER = new Intl.NumberFormat('es-CL');

function buildDashboardPath(basePath, scope, schoolId) {
  const params = new URLSearchParams({ scope });
  if (schoolId) params.set('colegio_id', schoolId);
  return `${basePath}?${params.toString()}`;
}

export function fetchDashboardResumen(scope, schoolId) {
  return apiClient.get(buildDashboardPath('/api/v1/dashboard/resumen/', scope, schoolId));
}

export function fetchDashboardExecutive(scope, schoolId) {
  return apiClient.get(buildDashboardPath('/api/v1/dashboard/executive/', scope, schoolId));
}

export function fetchDashboardSchools() {
  return apiClient.get('/api/v1/dashboard/colegios/');
}

export function formatValue(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return `${NUMBER_FORMATTER.format(value)}${suffix}`;
  return `${value}${suffix}`;
}

export function formatDateTime(value) {
  if (!value) return '';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleString('es-CL');
}