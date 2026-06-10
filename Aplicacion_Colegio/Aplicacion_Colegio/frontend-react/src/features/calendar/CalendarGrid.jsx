import { useMemo, useState } from 'react';

const DAYS_OF_WEEK = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

const DAY_NAMES = {
    1: 'Lunes',
    2: 'Martes',
    3: 'Miércoles',
    4: 'Jueves',
    5: 'Viernes',
    6: 'Sábado',
    0: 'Domingo',
};

export function CalendarGrid({ events, schedule, onEdit, canEdit, currentMonth, currentYear }) {
    // Use state to avoid hydration mismatch from new Date() in JSX
    const [todayStr] = useState(() => {
        const now = new Date();
        return now.toISOString().split('T')[0];
    });

    const year = currentYear ? Number(currentYear) : new Date().getFullYear();
    const month = currentMonth ? Number(currentMonth) - 1 : new Date().getMonth();

    const firstDayOfMonth = new Date(year, month, 1);
    const lastDayOfMonth = new Date(year, month + 1, 0);
    
    let startDayOfWeek = firstDayOfMonth.getDay() - 1;
    if (startDayOfWeek === -1) startDayOfWeek = 6;
    
    const daysInMonth = lastDayOfMonth.getDate();

    const monthLabel = useMemo(
        () => new Date(year, month).toLocaleString('es-ES', { month: 'long', year: 'numeric' }),
        [year, month]
    );
    
    const gridCells = useMemo(() => {
        const cells = [];
        for (let i = 0; i < startDayOfWeek; i++) {
            cells.push({ type: 'empty', key: `empty-start-${i}` });
        }
        
        for (let i = 1; i <= daysInMonth; i++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
            const dayOfWeekIndex = new Date(year, month, i).getDay();
            const scheduleKey = DAY_NAMES[dayOfWeekIndex];
            
            const dayEvents = events.filter(e => {
                if (!e.fecha_inicio) return false;
                return e.fecha_inicio.startsWith(dateStr);
            });
            
            const dayClasses = schedule && schedule[scheduleKey] ? schedule[scheduleKey] : [];
            
            cells.push({
                type: 'day',
                dayNumber: i,
                dateStr,
                events: dayEvents,
                classes: dayClasses,
                key: `day-${i}`
            });
        }
        
        const remainingCells = 7 - (cells.length % 7);
        if (remainingCells < 7) {
            for (let i = 0; i < remainingCells; i++) {
                cells.push({ type: 'empty', key: `empty-end-${i}` });
            }
        }
        
        return cells;
    }, [year, month, daysInMonth, startDayOfWeek, events, schedule]);

    function handleEventKeyDown(event, ev) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            if (onEdit) onEdit(ev);
        }
    }

    return (
        <div className="cal-grid-root">
            <div className="cal-grid-header">
                <h3 className="cal-grid-title">{monthLabel}</h3>
            </div>
            
            <div className="cal-grid">
                {DAYS_OF_WEEK.map(day => (
                    <div key={day} className="cal-grid-weekday">{day}</div>
                ))}
                
                {gridCells.map((cell) => {
                    if (cell.type === 'empty') {
                        return <div key={cell.key} className="cal-grid-cell cal-grid-cell--empty" />;
                    }
                    
                    const isToday = cell.dateStr === todayStr;
                    
                    return (
                        <div
                            key={cell.key}
                            className={`cal-grid-cell${isToday ? ' cal-grid-cell--today' : ''}`}
                        >
                            <span className={`cal-grid-day-number${isToday ? ' cal-grid-day-number--today' : ''}`}>
                                {cell.dayNumber}
                            </span>
                            
                            <div className="cal-grid-items">
                                {cell.classes && cell.classes.map(cls => (
                                    <div 
                                        key={`class-${cls.id}`} 
                                        className="cal-grid-class"
                                        title={`${cls.curso_nombre} - ${cls.asignatura_nombre}`}
                                    >
                                        <div className="cal-grid-class-name">
                                            {cls.hora_inicio.substring(0,5)} {cls.asignatura_nombre}
                                        </div>
                                        <div className="cal-grid-class-course">
                                            {cls.curso_nombre}
                                        </div>
                                    </div>
                                ))}

                                {cell.events.map(ev => (
                                    <div 
                                        key={ev.id_evento}
                                        role={canEdit ? 'button' : undefined}
                                        tabIndex={canEdit ? 0 : undefined}
                                        onClick={() => onEdit && onEdit(ev)}
                                        onKeyDown={canEdit ? (e) => handleEventKeyDown(e, ev) : undefined}
                                        className={`cal-grid-event${canEdit ? ' cal-grid-event--editable' : ''}`}
                                        style={{ backgroundColor: ev.color || '#10b981' }}
                                        title={ev.titulo}
                                    >
                                        {ev.hora_inicio ? `${ev.hora_inicio.substring(0,5)} ` : ''}{ev.titulo}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
