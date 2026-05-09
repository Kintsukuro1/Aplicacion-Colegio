import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { Card, CardHeader, CardBody, Badge, Button } from '@/components/ui';
import { hasCapability } from '@/lib/capabilities';
import { useTasks } from '@/lib/hooks';
import { useAuthStore } from '@/lib/store/useAuthStore';

export default function DashboardPage() {
  const navigate = useNavigate();
  const me = useAuthStore((state) => state.user);
  const { tasks, isLoading } = useTasks();
  const displayName = getFirstName(me?.full_name || me?.user?.name || me?.email);

  const stats = [
    {
      label: 'Pendientes',
      value: tasks?.filter((task) => task.estado === 'pendiente')?.length || 0,
      icon: 'PE',
      color: 'yellow',
    },
    {
      label: 'Entregadas',
      value: tasks?.filter((task) => task.estado === 'entregada')?.length || 0,
      icon: 'OK',
      color: 'green',
    },
    {
      label: 'Promedio',
      value: '7.8',
      icon: 'PR',
      color: 'purple',
    },
    {
      label: 'Asistencia',
      value: '95%',
      icon: 'AS',
      color: 'orange',
    },
  ];

  const upcomingEvents = [
    { date: 'Manana', title: 'Prueba de Lenguaje' },
    { date: 'Viernes', title: 'Entrega Proyecto' },
  ];

  const quickActions = useMemo(() => buildQuickActions(me), [me]);

  const getColorClass = (color) => {
    const colors = {
      yellow: 'bg-yellow-100 text-yellow-700',
      green: 'bg-green-100 text-green-700',
      purple: 'bg-violet-100 text-violet-700',
      orange: 'bg-orange-100 text-orange-700',
    };
    return colors[color] || colors.yellow;
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Bienvenido, {displayName || 'Usuario'}</h1>
        <p className="text-gray-600 mt-1">
          {new Date().toLocaleDateString('es-ES', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} variant="hover_lift">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">{stat.label}</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
              </div>
              <div className={`text-sm font-bold w-12 h-12 grid place-items-center rounded-lg ${getColorClass(stat.color)}`}>
                {stat.icon}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card variant="default">
            <CardHeader title="Proximas entregas" subtitle="Ordenadas por fecha" />
            <CardBody>
              {isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((item) => (
                    <div key={item} className="h-10 bg-gray-200 rounded animate-pulse" />
                  ))}
                </div>
              ) : tasks?.length ? (
                <div className="space-y-2">
                  {tasks.slice(0, 5).map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{task.titulo}</p>
                        <p className="text-xs text-gray-500">{task.asignatura}</p>
                      </div>
                      <Badge
                        variant={
                          task.estado === 'entregada'
                            ? 'success'
                            : task.estado === 'vencida'
                              ? 'error'
                              : 'warning'
                        }
                      >
                        {task.estado}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500 py-8">No hay tareas pendientes</p>
              )}
            </CardBody>
          </Card>

          <Card variant="default">
            <CardHeader title="Actividad reciente" />
            <CardBody>
              <div className="space-y-3">
                <ActivityItem
                  icon="NO"
                  title="Calificacion publicada"
                  description="Matematicas: 8.5"
                  time="Hace 2 horas"
                />
                <ActivityItem
                  icon="TA"
                  title="Tarea entregada"
                  description="Lenguaje - Ensayo"
                  time="Hace 1 dia"
                />
                <ActivityItem
                  icon="CO"
                  title="Nuevo comunicado"
                  description="Del Profesor de Ciencias"
                  time="Hace 3 dias"
                />
              </div>
            </CardBody>
          </Card>
        </div>

        <div className="space-y-6">
          <Card variant="hover_lift">
            <CardHeader title="Proximos eventos" />
            <CardBody>
              <div className="space-y-2">
                {upcomingEvents.map((event) => (
                  <div key={`${event.date}-${event.title}`} className="p-2 bg-blue-50 rounded-lg border-l-4 border-blue-500">
                    <p className="text-xs font-bold text-blue-600">{event.date}</p>
                    <p className="text-sm text-gray-900">{event.title}</p>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>

          <Card variant="default">
            <CardHeader title="Acciones rapidas" />
            <CardBody>
              <div className="space-y-2">
                {quickActions.map((action) => (
                  <Button
                    key={action.to}
                    variant="ghost"
                    className="w-full justify-start text-sm"
                    onClick={() => navigate(action.to)}
                  >
                    {action.label}
                  </Button>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ActivityItem({ icon, title, description, time }) {
  return (
    <div className="flex gap-3 pb-3 border-b border-gray-200 last:border-0">
      <div className="text-xs font-bold flex-shrink-0 w-8 h-8 rounded-lg bg-teal-100 text-teal-700 grid place-items-center">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 text-sm">{title}</p>
        <p className="text-xs text-gray-500">{description}</p>
        <p className="text-xs text-gray-400 mt-1">{time}</p>
      </div>
    </div>
  );
}

function getFirstName(value) {
  return String(value || '').trim().split(/\s+/)[0] || '';
}

function buildQuickActions(me) {
  if (hasCapability(me, 'PORTAL_ESTUDIANTE')) {
    return [
      { label: 'Mi panel', to: '/estudiante/panel' },
      { label: 'Mis notas', to: '/estudiante/panel#student-grades' },
      { label: 'Mi asistencia', to: '/estudiante/panel#student-attendance' },
      { label: 'Calendario escolar', to: '/calendario/eventos' },
    ];
  }

  if (hasCapability(me, 'CLASS_TAKE_ATTENDANCE') || hasCapability(me, 'CLASS_VIEW')) {
    return [
      { label: 'Mis clases', to: '/profesor/clases' },
      { label: 'Asistencias', to: '/profesor/asistencias' },
      { label: 'Calificaciones', to: '/profesor/calificaciones' },
      { label: 'Calendario escolar', to: '/calendario/eventos' },
    ];
  }

  return [
    { label: 'Estudiantes', to: '/admin-escolar/estudiantes' },
    { label: 'Cursos', to: '/admin-escolar/cursos' },
    { label: 'Calendario escolar', to: '/calendario/eventos' },
  ];
}
