import { useEffect, useState } from 'react';
import { formatGrade, formatShortDate, normalizeGrade } from '../../lib/formatters';
import EditableTableRow from '../../components/tables/EditableTableRow';
import { TableLoadingState } from '../../components/feedback/TableLoadingState';

function getEvaluationId(row) {
  return String(row.evaluacion ?? row.evaluacion_id ?? row.id_evaluacion ?? '');
}

function getStudentId(row) {
  return row.estudiante ?? row.estudiante_id ?? row.id_estudiante ?? '';
}

function buildEvaluationColumns(rows, evaluations) {
  const columns = new Map();

  evaluations.forEach((evaluation) => {
    const id = String(evaluation.id_evaluacion ?? evaluation.id ?? '');
    if (!id) return;
    columns.set(id, {
      id,
      name: evaluation.nombre || `Evaluacion ${columns.size + 1}`,
      date: evaluation.fecha_evaluacion,
    });
  });

  rows.forEach((row) => {
    const id = getEvaluationId(row);
    if (!id || columns.has(id)) return;
    columns.set(id, {
      id,
      name: row.evaluacion_nombre || `Evaluacion ${columns.size + 1}`,
      date: row.fecha_evaluacion,
    });
  });

  return Array.from(columns.values());
}

function buildGroupedRows(rows, evaluationColumns) {
  const grouped = new Map();

  rows.forEach((row) => {
    const studentId = getStudentId(row);
    const key = String(studentId || row.estudiante_nombre || row.id_calificacion);
    const existing = grouped.get(key) || {
      studentId,
      studentName: row.estudiante_nombre || 'Sin estudiante',
      grades: new Map(),
      latestDate: '',
    };

    existing.grades.set(getEvaluationId(row), row);

    const dateValue = String(row.fecha_creacion || '');
    if (dateValue > existing.latestDate) {
      existing.latestDate = dateValue;
    }

    grouped.set(key, existing);
  });

  return Array.from(grouped.values()).sort((a, b) => {
    const nameCompare = String(a.studentName || '').localeCompare(String(b.studentName || ''));
    if (nameCompare !== 0) {
      return nameCompare;
    }
    return Number(a.studentId || 0) - Number(b.studentId || 0);
  }).map((row) => ({
    ...row,
    evaluationSummary: evaluationColumns.length ? evaluationColumns.map((evaluation) => evaluation.name).join(', ') : '-',
  }));
}

function AllEvaluationsTable({ rows, evaluations }) {
  const evaluationColumns = buildEvaluationColumns(rows, evaluations);
  const groupedRows = buildGroupedRows(rows, evaluationColumns);
  const emptyColSpan = Math.max(4, 4 + evaluationColumns.length);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Evaluaciones</th>
            <th>Estudiante</th>
            {evaluationColumns.map((evaluation, index) => (
              <th key={evaluation.id} title={`${evaluation.name} ${formatShortDate(evaluation.date, '')}`.trim()}>
                <span className="gradebook-note-head">
                  {index === 0 ? 'Nota' : `Nota ${index + 1}`}
                  <small>{evaluation.name}</small>
                </span>
              </th>
            ))}
            <th>Fecha</th>
          </tr>
        </thead>
        <tbody>
          {groupedRows.map((row) => (
            <tr key={row.studentId || row.studentName}>
              <td>{row.studentId || '-'}</td>
              <td title={row.evaluationSummary}>{row.evaluationSummary}</td>
              <td>{row.studentName}</td>
              {evaluationColumns.map((evaluation) => {
                const gradeRow = row.grades.get(evaluation.id);
                const normalizedGrade = normalizeGrade(gradeRow?.nota);
                const isLowGrade = normalizedGrade !== null && normalizedGrade < 4;

                return (
                  <td key={evaluation.id}>
                    <span className={isLowGrade ? 'grade-low' : undefined}>
                      {formatGrade(gradeRow?.nota, '-')}
                    </span>
                  </td>
                );
              })}
              <td>{formatShortDate(row.latestDate)}</td>
            </tr>
          ))}
          {groupedRows.length === 0 ? (
            <tr>
              <td colSpan={emptyColSpan}>Sin registros</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function InlineEditGrade({ row, isSaving, onSave, onCancel }) {
  const [draftNota, setDraftNota] = useState(normalizeGrade(row.nota) ?? '');
  const normalizedDraftNota = normalizeGrade(draftNota);
  const isDraftLowGrade = normalizedDraftNota !== null && normalizedDraftNota < 4;

  useEffect(() => {
    setDraftNota(normalizeGrade(row.nota) ?? '');
  }, [row.nota]);

  return (
    <>
      <td>{row.id_calificacion}</td>
      <td>{row.evaluacion_nombre || row.evaluacion || '-'}</td>
      <td>{row.estudiante_nombre}</td>
      <td>
        <input
          type="number"
          step="0.1"
          className={isDraftLowGrade ? 'grade-low' : undefined}
          style={{ width: '80px', padding: '0.2rem' }}
          value={draftNota}
          onChange={(e) => setDraftNota(e.target.value)}
          disabled={isSaving}
        />
      </td>
      <td>{formatShortDate(row.fecha_creacion)}</td>
      <td className="actions-cell">
        <button
          type="button"
          className="small"
          disabled={isSaving}
          onClick={() => onSave({ nota: draftNota })}
        >
          Guardar
        </button>
        <button type="button" className="small secondary" disabled={isSaving} onClick={onCancel}>
          Cancelar
        </button>
      </td>
    </>
  );
}

export function TeacherGradesTable({ rows, evaluations = [], loading, canEdit, canDelete, onUpdate, onDelete, showAllEvaluations = false }) {
  if (loading) {
    return <TableLoadingState />;
  }

  if (showAllEvaluations) {
    return <AllEvaluationsTable rows={rows} evaluations={evaluations} />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Evaluacion</th>
            <th>Estudiante</th>
            <th>Nota</th>
            <th>Fecha</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const normalizedGrade = normalizeGrade(row.nota);
            const isLowGrade = normalizedGrade !== null && normalizedGrade < 4;

            return (
            <EditableTableRow
              key={row.id_calificacion}
              onSave={async (data) => onUpdate(row.id_calificacion, data)}
              ViewComponent={({ onEdit }) => (
                <>
                  <td>{row.id_calificacion}</td>
                  <td>{row.evaluacion_nombre || row.evaluacion || '-'}</td>
                  <td>{row.estudiante_nombre}</td>
                  <td>
                    <span className={isLowGrade ? 'grade-low' : undefined}>
                      {formatGrade(row.nota, '-')}
                    </span>
                  </td>
                  <td>{formatShortDate(row.fecha_creacion)}</td>
                  <td className="actions-cell">
                    {canEdit ? (
                      <button type="button" className="small" onClick={onEdit}>
                        Editar
                      </button>
                    ) : null}
                    {canDelete ? (
                      <button type="button" className="small danger" onClick={() => onDelete(row.id_calificacion)}>
                        Eliminar
                      </button>
                    ) : null}
                    {!canEdit && !canDelete ? <span>Solo lectura</span> : null}
                  </td>
                </>
              )}
              EditComponent={({ onSave, onCancel, isSaving }) => (
                <InlineEditGrade row={row} isSaving={isSaving} onSave={onSave} onCancel={onCancel} />
              )}
            />
          );
          })}
          {!loading && rows.length === 0 ? (
            <tr>
              <td colSpan="6">Sin registros</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
