import { useEffect, useRef } from 'react';
import { formatGrade, normalizeGrade } from '../../lib/formatters';
import EditableTableRow from '../../components/tables/EditableTableRow';
import { TableLoadingState } from '../../components/feedback/TableLoadingState';

function InlineEditGrade({ row, isSaving, onSave, onCancel }) {
  const notaRef = useRef(normalizeGrade(row.nota) ?? '');

  useEffect(() => {
    notaRef.current = normalizeGrade(row.nota) ?? '';
  }, [row.nota]);

  return (
    <>
      <td>{row.id_calificacion}</td>
      <td>{row.estudiante_nombre}</td>
      <td>
        <input
          type="number"
          step="0.1"
          style={{ width: '80px', padding: '0.2rem' }}
          defaultValue={normalizeGrade(row.nota) ?? ''}
          onChange={(e) => {
            notaRef.current = e.target.value;
          }}
          disabled={isSaving}
        />
      </td>
      <td>{row.fecha_creacion}</td>
      <td className="actions-cell">
        <button
          type="button"
          className="small"
          disabled={isSaving}
          onClick={() => onSave({ nota: notaRef.current })}
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

export function TeacherGradesTable({ rows, loading, canEdit, canDelete, onUpdate, onDelete }) {
  if (loading) {
    return <TableLoadingState />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
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
                  <td>{row.estudiante_nombre}</td>
                  <td>
                    <span className={isLowGrade ? 'grade-low' : undefined}>
                      {formatGrade(row.nota, '-')}
                    </span>
                  </td>
                  <td>{row.fecha_creacion}</td>
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
              <td colSpan="5">Sin registros</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
