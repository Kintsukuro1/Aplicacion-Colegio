import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/apiClient';
import { SectionStatus } from './StudentSelfCommon';

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

export function StudentTaskCalendarTab() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [selectedDateStr, setSelectedDateStr] = useState(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  });

  const { data: tasks = [], isLoading, error } = useQuery({
    queryKey: ['student-tasks'],
    queryFn: () => apiClient.get('/api/v1/estudiante/tareas/'),
  });

  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth();

  const calendarCells = useMemo(() => {
    // Primer día del mes
    const firstDayOfMonth = new Date(currentYear, currentMonth, 1);
    // El día de la semana del primer día del mes: 0 (Domingo) al 6 (Sábado)
    let startDayOfWeek = firstDayOfMonth.getDay();
    // Convertir de formato Domingo-Primero a Lunes-Primero (Lunes=0, Domingo=6)
    startDayOfWeek = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;

    // Número total de días en el mes
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

    const cells = [];
    // Rellenar días en blanco del mes anterior
    for (let i = 0; i < startDayOfWeek; i++) {
      cells.push({ isPadding: true, dayNum: null, dateStr: null });
    }

    // Agregar días reales del mes
    for (let day = 1; day <= daysInMonth; day++) {
      const d = new Date(currentYear, currentMonth, day);
      const yearStr = d.getFullYear();
      const monthStr = String(d.getMonth() + 1).padStart(2, '0');
      const dayStr = String(d.getDate()).padStart(2, '0');
      const dateStr = `${yearStr}-${monthStr}-${dayStr}`;

      cells.push({
        isPadding: false,
        dayNum: day,
        dateStr,
      });
    }

    return cells;
  }, [currentYear, currentMonth]);

  // Agrupar tareas por fecha de entrega
  const tasksByDate = useMemo(() => {
    const map = {};
    for (const task of tasks) {
      if (task.fecha_entrega_date) {
        if (!map[task.fecha_entrega_date]) {
          map[task.fecha_entrega_date] = [];
        }
        map[task.fecha_entrega_date].push(task);
      }
    }
    return map;
  }, [tasks]);

  const selectedDayTasks = useMemo(() => {
    return tasksByDate[selectedDateStr] || [];
  }, [tasksByDate, selectedDateStr]);

  function handlePrevMonth() {
    setCurrentDate(new Date(currentYear, currentMonth - 1, 1));
  }

  function handleNextMonth() {
    setCurrentDate(new Date(currentYear, currentMonth + 1, 1));
  }

  function handleToday() {
    const today = new Date();
    setCurrentDate(today);
    setSelectedDateStr(today.toISOString().split('T')[0]);
  }

  return (
    <article className="card section-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ margin: 0 }}>Calendario de Tareas</h3>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
            Fechas límite y entregas mensuales en un solo lugar.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-secondary"
            style={{
              padding: '0.4rem 0.8rem',
              fontSize: '0.85rem',
              borderRadius: '6px',
              cursor: 'pointer',
              background: 'rgba(148, 163, 184, 0.08)',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              color: 'var(--text)',
              fontWeight: '500',
            }}
            onClick={handlePrevMonth}
          >
            ◀ Anterior
          </button>
          <strong style={{ fontSize: '1rem', minWidth: '130px', textAlign: 'center' }}>
            {MESES[currentMonth]} {currentYear}
          </strong>
          <button
            type="button"
            className="btn-secondary"
            style={{
              padding: '0.4rem 0.8rem',
              fontSize: '0.85rem',
              borderRadius: '6px',
              cursor: 'pointer',
              background: 'rgba(148, 163, 184, 0.08)',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              color: 'var(--text)',
              fontWeight: '500',
            }}
            onClick={handleNextMonth}
          >
            Siguiente ▶
          </button>
          <button
            type="button"
            className="btn-secondary"
            style={{
              padding: '0.4rem 0.8rem',
              fontSize: '0.85rem',
              borderRadius: '6px',
              cursor: 'pointer',
              background: 'rgba(148, 163, 184, 0.08)',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              color: 'var(--text)',
              fontWeight: '500',
              marginLeft: '0.5rem',
            }}
            onClick={handleToday}
          >
            Hoy
          </button>
        </div>
      </div>

      {isLoading ? (
        <SectionStatus title="Cargando calendario" description="Sincronizando las fechas límite de entrega..." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">
          {error?.message || 'Error al cargar el calendario.'}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
          {/* Calendar Month Grid */}
          <div style={{ width: '100%' }}>
            {/* Days of week header */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                textAlign: 'center',
                fontWeight: '600',
                fontSize: '0.85rem',
                color: 'var(--muted)',
                marginBottom: '0.5rem',
              }}
            >
              {DIAS_SEMANA.map((day) => (
                <div key={day} style={{ padding: '0.35rem' }}>
                  {day}
                </div>
              ))}
            </div>

            {/* Monthly grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: '4px',
                background: 'rgba(148, 163, 184, 0.04)',
                padding: '4px',
                borderRadius: '8px',
                border: '1px solid rgba(148, 163, 184, 0.08)',
              }}
            >
              {calendarCells.map((cell, index) => {
                const dayTasks = cell.dateStr ? tasksByDate[cell.dateStr] || [] : [];
                const isSelected = cell.dateStr === selectedDateStr;
                const hasPending = dayTasks.some((t) => t.estado === 'pendiente' || t.estado === 'atrasada');
                const hasCorrected = dayTasks.some((t) => t.estado === 'corregida');
                const hasSubmitted = dayTasks.some((t) => t.estado === 'entregada');

                const isToday = cell.dateStr === new Date().toISOString().split('T')[0];

                return (
                  <div
                    key={index}
                    onClick={() => cell.dateStr && setSelectedDateStr(cell.dateStr)}
                    style={{
                      height: '60px',
                      background: cell.isPadding
                        ? 'transparent'
                        : isSelected
                        ? 'rgba(59, 130, 246, 0.15)'
                        : 'rgba(255, 255, 255, 0.02)',
                      border: cell.isPadding
                        ? 'none'
                        : isSelected
                        ? '1px solid rgba(59, 130, 246, 0.5)'
                        : isToday
                        ? '1px solid rgba(148, 163, 184, 0.4)'
                        : '1px solid rgba(148, 163, 184, 0.06)',
                      borderRadius: '6px',
                      padding: '0.35rem',
                      cursor: cell.isPadding ? 'default' : 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      transition: 'background 0.2s, border 0.2s',
                    }}
                  >
                    {!cell.isPadding && (
                      <>
                        <span
                          style={{
                            fontSize: '0.85rem',
                            fontWeight: isToday || isSelected ? '700' : '500',
                            color: isSelected ? 'var(--primary)' : 'var(--text)',
                          }}
                        >
                          {cell.dayNum}
                        </span>

                        {/* Task indicators dots */}
                        {dayTasks.length > 0 && (
                          <div style={{ display: 'flex', gap: '3px', width: '100%', flexWrap: 'wrap' }}>
                            {hasPending && (
                              <span
                                title="Tareas pendientes"
                                style={{
                                  width: '6px',
                                  height: '6px',
                                  borderRadius: '50%',
                                  background: '#ef4444',
                                }}
                              />
                            )}
                            {hasSubmitted && (
                              <span
                                title="Tareas entregadas"
                                style={{
                                  width: '6px',
                                  height: '6px',
                                  borderRadius: '50%',
                                  background: '#3b82f6',
                                }}
                              />
                            )}
                            {hasCorrected && (
                              <span
                                title="Tareas corregidas"
                                style={{
                                  width: '6px',
                                  height: '6px',
                                  borderRadius: '50%',
                                  background: '#10b981',
                                }}
                              />
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Details panel for selected day */}
          <div
            style={{
              borderTop: '1px solid rgba(148, 163, 184, 0.12)',
              paddingTop: '1.25rem',
            }}
          >
            <h4 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '600' }}>
              Tareas para el {selectedDateStr ? new Date(selectedDateStr + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) : ''}
            </h4>

            {selectedDayTasks.length === 0 ? (
              <div style={{ color: 'var(--muted)', fontSize: '0.9rem', padding: '1rem', background: 'rgba(148, 163, 184, 0.03)', borderRadius: '6px', border: '1px dashed rgba(148, 163, 184, 0.15)' }}>
                No tienes tareas programadas para entregar en este día.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {selectedDayTasks.map((task) => {
                  const statusColors = {
                    corregida: { bg: 'rgba(16, 185, 129, 0.1)', text: '#10b981' },
                    entregada: { bg: 'rgba(59, 130, 246, 0.1)', text: '#3b82f6' },
                    atrasada: { bg: 'rgba(245, 158, 11, 0.1)', text: '#f59e0b' },
                    pendiente: { bg: 'rgba(107, 114, 128, 0.1)', text: '#6b7280' },
                  };
                  const colors = statusColors[task.estado] || statusColors.pendiente;

                  return (
                    <div
                      key={task.id_tarea}
                      style={{
                        padding: '1rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(148, 163, 184, 0.1)',
                        borderRadius: '8px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '0.75rem',
                      }}
                    >
                      <div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--muted)', fontWeight: '500' }}>
                          {task.asignatura_nombre || 'Asignatura'}
                        </span>
                        <h5 style={{ margin: '0.15rem 0', fontSize: '0.95rem', fontWeight: '600' }}>
                          {task.titulo}
                        </h5>
                        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted)' }}>
                          Hora límite: {task.fecha_entrega_time || 'Sin hora'}
                        </p>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {task.estado === 'corregida' && task.calificacion && (
                          <strong style={{ color: '#10b981', fontSize: '1rem', marginRight: '0.5rem' }}>
                            Nota: {task.calificacion.toFixed(1)}
                          </strong>
                        )}
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            padding: '0.25rem 0.6rem',
                            borderRadius: '999px',
                            background: colors.bg,
                            color: colors.text,
                            border: `1px solid ${colors.text}2b`,
                          }}
                        >
                          {task.icono_estado} {task.texto_estado}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
