export const ATTENDANCE_STATES = [
  { value: 'P', label: 'Presente' },
  { value: 'A', label: 'Ausente' },
  { value: 'T', label: 'Tardanza' },
  { value: 'J', label: 'Justificada' },
];

export function isBatchEndpointUnavailable(error) {
  return error?.status === 404 || error?.status === 405;
}

export function toBulkResult(payload, fallbackFailedIds = []) {
  const failedIds = Array.isArray(payload?.failed_ids)
    ? payload.failed_ids
    : Array.isArray(payload?.failedIds)
      ? payload.failedIds
      : fallbackFailedIds;

  const success = Number.isFinite(payload?.success) ? payload.success : 0;
  const failed = Number.isFinite(payload?.failed) ? payload.failed : failedIds.length;
  return { success, failed, failedIds };
}

export function createInitialState(searchParams) {
  const initialClass = searchParams.get('clase_id') || '';
  const initialDate = searchParams.get('fecha') || '';
  const initialPage = Number.parseInt(searchParams.get('page') || '1', 10);

  return {
    selectedClass: initialClass,
    selectedDate: initialDate,
    page: Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1,
    classes: [],
    rows: [],
    selectedIds: [],
    form: {
      clase: initialClass,
      estudiante: '',
      fecha: initialDate,
      estado: 'P',
      tipo_asistencia: '',
      observaciones: '',
    },
    editingId: null,
    bulkState: 'P',
    processingBulk: false,
    saving: false,
    bulkResult: null,
  };
}

export function adminAttendanceReducer(state, action) {
  switch (action.type) {
    case 'SET_FILTERS':
      return {
        ...state,
        selectedClass: action.selectedClass,
        selectedDate: action.selectedDate,
        page: action.page ?? 1,
        selectedIds: [],
        bulkResult: null,
        form: {
          ...state.form,
          clase: state.form.clase || action.selectedClass || '',
          fecha: state.form.fecha || action.selectedDate || '',
        },
      };
    case 'SET_PAGE':
      return { ...state, page: action.page, selectedIds: [], bulkResult: null };
    case 'SET_CLASSES':
      return { ...state, classes: action.classes };
    case 'SET_ROWS':
      return { ...state, rows: action.rows, selectedIds: [] };
    case 'SET_FORM_FIELD':
      return { ...state, form: { ...state.form, [action.name]: action.value } };
    case 'START_EDIT':
      return {
        ...state,
        editingId: action.row.id_asistencia,
        form: {
          clase: action.row.clase ? String(action.row.clase) : state.selectedClass,
          estudiante: action.row.estudiante ? String(action.row.estudiante) : '',
          fecha: action.row.fecha || '',
          estado: action.row.estado || 'P',
          tipo_asistencia: action.row.tipo_asistencia || '',
          observaciones: action.row.observaciones || '',
        },
      };
    case 'RESET_FORM':
      return {
        ...state,
        editingId: null,
        form: {
          clase: state.selectedClass || '',
          estudiante: '',
          fecha: state.selectedDate || '',
          estado: 'P',
          tipo_asistencia: '',
          observaciones: '',
        },
      };
    case 'TOGGLE_SELECT': {
      const id = action.id;
      const prev = state.selectedIds;
      return { ...state, selectedIds: prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id] };
    }
    case 'TOGGLE_SELECT_ALL': {
      const currentIds = state.rows.map((row) => row.id_asistencia);
      const allSelected = currentIds.length > 0 && currentIds.every((id) => state.selectedIds.includes(id));
      return { ...state, selectedIds: allSelected ? [] : currentIds };
    }
    case 'SET_BULK_STATE': return { ...state, bulkState: action.value };
    case 'SET_PROCESSING_BULK': return { ...state, processingBulk: action.value };
    case 'SET_SAVING': return { ...state, saving: action.value };
    case 'SET_BULK_RESULT': return { ...state, bulkResult: action.value };
    default: return state;
  }
}
