import { useMemo } from 'react';
import { SectionStatus, EmptySection } from './StudentSelfCommon';

export function StudentClassesTab({ classes, loading, error }) {
  const uniqueClasses = useMemo(() => {
    if (!classes) return [];
    const seen = new Set();
    return classes.filter(item => {
      const asignatura = item.asignatura_nombre || item.asignatura || item.nombre || 'Asignatura';
      const curso = item.curso_nombre || item.curso || 'Curso no disponible';
      const key = `${asignatura}-${curso}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [classes]);

  return (
    <article className="card section-card">
      <h3>Mis Clases</h3>
      {loading ? (
        <SectionStatus title="Cargando clases" description="Preparando el listado de asignaturas activas." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">{error}</div>
      ) : uniqueClasses?.length ? (
        <ul className="compact-list">
          {uniqueClasses.map((item) => (
            <li key={item.id_clase_estudiante || item.clase_id || item.id || `${item.curso_nombre}-${item.asignatura_nombre}`}>
              <strong>{item.asignatura_nombre || item.asignatura || item.nombre || 'Asignatura'}</strong>
              <span>{item.curso_nombre || item.curso || 'Curso no disponible'}</span>
            </li>
          ))}
        </ul>
      ) : (
        <EmptySection title="Sin clases asignadas" description="Todavía no hay asignaturas registradas para este ciclo." />
      )}
    </article>
  );
}
