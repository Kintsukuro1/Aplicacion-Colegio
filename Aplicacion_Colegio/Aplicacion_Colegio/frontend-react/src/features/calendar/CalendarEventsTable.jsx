export function CalendarEventsTable({ events, canEdit, savingId, onEdit, onDelete }) {
  if (!events || events.length === 0) {
    return (
      <article className="card section-card">
        <h3>Resultados</h3>
        <p className="section-muted">No se encontraron eventos para los filtros seleccionados.</p>
      </article>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Titulo</th>
            <th>Tipo</th>
            <th>Fecha</th>
            <th>Hora</th>
            <th>Visibilidad</th>
            <th>Color</th>
            {canEdit && <th>Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {events.map((evt) => (
            <tr key={evt.id}>
              <td>{evt.id}</td>
              <td>
                {evt.titulo}
                {evt.es_feriado_nacional && <span className="badge badge-info" style={{ marginLeft: 8 }}>Feriado</span>}
              </td>
              <td style={{ textTransform: 'capitalize' }}>{evt.tipo}</td>
              <td>
                {evt.fecha_inicio} {evt.fecha_fin && evt.fecha_fin !== evt.fecha_inicio ? ` al ${evt.fecha_fin}` : ''}
              </td>
              <td>{evt.todo_el_dia ? 'Todo el dia' : `${evt.hora_inicio || ''} - ${evt.hora_fin || ''}`}</td>
              <td style={{ textTransform: 'capitalize' }}>{evt.visibilidad}</td>
              <td>
                <div
                  style={{
                    width: 24,
                    height: 24,
                    backgroundColor: evt.color,
                    borderRadius: 4,
                    border: '1px solid var(--border-color)',
                  }}
                  title={evt.color}
                />
              </td>
              {canEdit && (
                <td>
                  <div className="actions-cell">
                    <button type="button" className="small secondary" onClick={() => onEdit(evt)} disabled={savingId === evt.id}>
                      Editar
                    </button>
                    <button type="button" className="small danger" onClick={() => onDelete(evt)} disabled={savingId === evt.id}>
                      Eliminar
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
