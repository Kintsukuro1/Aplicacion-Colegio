import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../components/feedback/Toast';
import { getAccessToken } from '../../stores/authStore';
import { SectionStatus, EmptySection } from './StudentSelfCommon';

export function StudentTasksTab() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('todas');
  const [selectedTask, setSelectedTask] = useState(null);
  const [comentario, setComentario] = useState('');
  const [archivo, setArchivo] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { data: tasks = [], isLoading, error } = useQuery({
    queryKey: ['student-tasks'],
    queryFn: () => apiClient.get('/api/v1/estudiante/tareas/'),
  });

  const filteredTasks = tasks.filter((task) => {
    if (filter === 'todas') return true;
    if (filter === 'pendientes') return task.estado === 'pendiente' || task.estado === 'atrasada';
    if (filter === 'entregadas') return task.estado === 'entregada';
    if (filter === 'corregidas') return task.estado === 'corregida';
    return true;
  });

  async function handleEntregaSubmit(e, taskId) {
    e.preventDefault();
    if (!archivo) {
      toast.error('Por favor, selecciona un archivo para entregar.');
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('tarea_id', taskId);
      formData.append('archivo', archivo);
      if (comentario) {
        formData.append('comentario', comentario);
      }

      const access = getAccessToken();
      const headers = {};
      if (access) {
        headers.Authorization = `Bearer ${access}`;
      }

      const response = await fetch(`${apiClient.baseUrl}/api/v1/estudiante/tareas/entregar/`, {
        method: 'POST',
        headers,
        body: formData,
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || 'No se pudo entregar la tarea.');
      }

      toast.success(result.mensaje || 'Tarea entregada exitosamente.');
      setArchivo(null);
      setComentario('');
      setSelectedTask(null);
      await queryClient.invalidateQueries({ queryKey: ['student-tasks'] });
    } catch (err) {
      toast.error(err.message || 'Ocurrió un error al entregar la tarea.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <article className="card section-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        <h3>Mis Tareas</h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['todas', 'pendientes', 'entregadas', 'corregidas'].map((mode) => (
            <button
              key={mode}
              type="button"
              className={`badge ${filter === mode ? 'badge-warning' : 'badge-inactive'}`}
              style={{ border: 'none', cursor: 'pointer', padding: '0.4rem 0.8rem', textTransform: 'capitalize' }}
              onClick={() => setFilter(mode)}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <SectionStatus title="Cargando tareas" description="Obteniendo las tareas y actividades programadas para tu curso." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">
          {error?.message || 'Error al cargar las tareas.'}
        </div>
      ) : filteredTasks.length === 0 ? (
        <EmptySection title="Sin tareas" description={`No hay tareas en la sección "${filter}".`} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {filteredTasks.map((task) => {
            const urgencyTone =
              task.estado_tiempo === 'vencida'
                ? 'danger'
                : task.estado_tiempo === 'urgente'
                ? 'danger'
                : task.estado_tiempo === 'proximo'
                ? 'warning'
                : 'inactive';

            const statusLabel =
              task.estado === 'corregida'
                ? 'Corregida'
                : task.estado === 'entregada'
                ? 'Entregada'
                : task.estado === 'atrasada'
                ? 'Atrasada'
                : 'Pendiente';

            const statusColor =
              task.estado === 'corregida'
                ? '#15803d'
                : task.estado === 'entregada'
                ? '#2563eb'
                : task.estado === 'atrasada'
                ? '#d97706'
                : '#6b7280';

            const isSelected = selectedTask === task.id_tarea;

            return (
              <div
                key={task.id_tarea}
                className="card"
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(148, 163, 184, 0.12)',
                  padding: '1.25rem',
                  borderRadius: '8px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: '500' }}>
                      {task.asignatura_nombre || 'Asignatura'}
                    </span>
                    <h4 style={{ margin: '0.2rem 0 0.4rem 0', fontSize: '1.1rem', fontWeight: '600' }}>
                      {task.titulo}
                    </h4>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span
                      className={`badge ${urgencyTone === 'danger' ? 'badge-danger' : urgencyTone === 'warning' ? 'badge-warning' : 'badge-inactive'}`}
                      style={{ fontSize: '0.75rem' }}
                    >
                      {task.fecha_entrega_full}
                    </span>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        padding: '0.25rem 0.6rem',
                        borderRadius: '999px',
                        background: `${statusColor}1c`,
                        color: statusColor,
                        border: `1px solid ${statusColor}40`,
                      }}
                    >
                      {task.icono_estado} {statusLabel}
                    </span>
                  </div>
                </div>

                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text)', whiteSpace: 'pre-line' }}>
                  {task.instrucciones || 'Sin instrucciones adicionales.'}
                </p>

                {task.archivo_instrucciones && (
                  <div style={{ marginTop: '0.25rem' }}>
                    <a
                      href={`${apiClient.baseUrl}${task.archivo_instrucciones}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        fontSize: '0.85rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        color: 'var(--primary)',
                        textDecoration: 'none',
                        fontWeight: '500',
                      }}
                    >
                      📎 Descargar Archivo de Instrucciones
                    </a>
                  </div>
                )}

                {task.estado === 'corregida' && (
                  <div
                    style={{
                      background: 'rgba(21, 128, 61, 0.05)',
                      border: '1px solid rgba(21, 128, 61, 0.15)',
                      borderRadius: '6px',
                      padding: '0.75rem 1rem',
                      marginTop: '0.5rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <strong style={{ color: '#15803d', fontSize: '0.85rem' }}>Nota Recibida:</strong>
                      <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#15803d' }}>
                        {task.calificacion ? task.calificacion.toFixed(1) : '-'}
                      </span>
                    </div>
                    {task.entrega?.retroalimentacion && (
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text)' }}>
                        <strong>Feedback del profesor:</strong> {task.entrega.retroalimentacion}
                      </p>
                    )}
                  </div>
                )}

                {task.entrega && task.estado !== 'corregida' && (
                  <div
                    style={{
                      background: 'rgba(37, 99, 235, 0.04)',
                      border: '1px solid rgba(37, 99, 235, 0.15)',
                      borderRadius: '6px',
                      padding: '0.75rem 1rem',
                      marginTop: '0.25rem',
                    }}
                  >
                    <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                      Entregada el {new Date(task.entrega.fecha_entrega).toLocaleString()}
                    </span>
                    {task.entrega.comentario_estudiante && (
                      <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
                        <strong>Tu comentario:</strong> {task.entrega.comentario_estudiante}
                      </p>
                    )}
                    {task.entrega.archivo && (
                      <div style={{ marginTop: '0.35rem' }}>
                        <a
                          href={`${apiClient.baseUrl}${task.entrega.archivo}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ fontSize: '0.8rem', color: 'var(--primary)' }}
                        >
                          📥 Ver archivo entregado
                        </a>
                      </div>
                    )}
                  </div>
                )}

                {task.estado !== 'corregida' && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {!isSelected ? (
                      <button
                        type="button"
                        style={{
                          alignSelf: 'flex-start',
                          padding: '0.4rem 1rem',
                          fontSize: '0.85rem',
                          background: 'rgba(148, 163, 184, 0.08)',
                          border: '1px solid rgba(148, 163, 184, 0.2)',
                          color: 'var(--text)',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontWeight: '500',
                        }}
                        onClick={() => {
                          setSelectedTask(task.id_tarea);
                          setArchivo(null);
                          setComentario('');
                        }}
                      >
                        {task.entrega ? '✏️ Actualizar Entrega' : '📤 Entregar Tarea'}
                      </button>
                    ) : (
                      <form
                        onSubmit={(e) => handleEntregaSubmit(e, task.id_tarea)}
                        style={{
                          background: 'rgba(148, 163, 184, 0.05)',
                          border: '1px solid rgba(148, 163, 184, 0.15)',
                          padding: '1rem',
                          borderRadius: '6px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.75rem',
                        }}
                      >
                        <h5 style={{ margin: 0, fontSize: '0.9rem', fontWeight: '600' }}>
                          {task.entrega ? 'Reemplazar entrega actual' : 'Nueva entrega'}
                        </h5>
                        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.85rem' }}>
                          Archivo de Tarea (PDF, ZIP, DOCX, etc.)
                          <input
                            type="file"
                            required
                            onChange={(e) => setArchivo(e.target.files?.[0] || null)}
                            disabled={submitting}
                            style={{
                              padding: '0.35rem',
                              background: 'rgba(0, 0, 0, 0.1)',
                              border: '1px solid rgba(148, 163, 184, 0.2)',
                              borderRadius: '4px',
                              color: 'var(--text)',
                            }}
                          />
                        </label>
                        <label style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.85rem' }}>
                          Comentario para el profesor (Opcional)
                          <textarea
                            rows="2"
                            value={comentario}
                            onChange={(e) => setComentario(e.target.value)}
                            disabled={submitting}
                            placeholder="Escribe un comentario adicional sobre tu entrega..."
                            style={{
                              padding: '0.5rem',
                              background: 'rgba(0, 0, 0, 0.1)',
                              border: '1px solid rgba(148, 163, 184, 0.2)',
                              borderRadius: '4px',
                              color: 'var(--text)',
                              resize: 'vertical',
                            }}
                          />
                        </label>
                        <div style={{ display: 'flex', gap: '0.5rem', alignSelf: 'flex-start' }}>
                          <button
                            type="submit"
                            disabled={submitting}
                            style={{
                              padding: '0.4rem 1.2rem',
                              fontSize: '0.85rem',
                              background: 'var(--primary, #3b82f6)',
                              color: '#fff',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontWeight: '600',
                            }}
                          >
                            {submitting ? 'Subiendo...' : task.entrega ? 'Actualizar' : 'Entregar'}
                          </button>
                          <button
                            type="button"
                            disabled={submitting}
                            style={{
                              padding: '0.4rem 1rem',
                              fontSize: '0.85rem',
                              background: 'transparent',
                              border: '1px solid rgba(148, 163, 184, 0.3)',
                              color: 'var(--text)',
                              borderRadius: '4px',
                              cursor: 'pointer',
                            }}
                            onClick={() => setSelectedTask(null)}
                          >
                            Cancelar
                          </button>
                        </div>
                      </form>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}
