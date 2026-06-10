import React from 'react';
import { PageTransition } from '@/components/PageTransition';
import { CardEnhanced } from '@/components/CardEnhanced';
import {
  SkeletonLine,
  SkeletonCard,
  SkeletonGrid,
  SkeletonTable,
  SkeletonAvatar,
  SkeletonText,
  SkeletonPresets,
} from '@/components/SkeletonAnimated';
import { useToast } from '@/components/ToastAnimated';
import { useTasks } from '@/lib/hooks';

/**
 * FASE 5.4 - EJEMPLOS PRACTICOS
 * 
 * 6 ejemplos mostrando todas las animaciones en contexto real
 */

// ============================================================================
// EJEMPLO 1: Dashboard con PageTransition + Stats Skeleton
// ============================================================================

export function AnimatedDashboardExample() {
  const { tasks, isLoading } = useTasks();
  const toast = useToast();

  const stats = [
    { label: 'Pendientes', value: 5, icon: '⏳' },
    { label: 'Completadas', value: 12, icon: '✓' },
    { label: 'Promedio', value: '7.8', icon: '📊' },
    { label: 'Asistencia', value: '95%', icon: '📅' },
  ];

  return (
    <PageTransition>
      <div className="p-6 space-y-6">
        <h1 className="text-3xl font-semibold">Dashboard Animado</h1>

        {/* Stats con Skeleton Loading */}
        {isLoading ? (
          <SkeletonPresets.statsGrid />
        ) : (
          <div className="grid grid-cols-4 gap-4">
            {stats.map((stat) => (
              <CardEnhanced
                key={stat.label}
                variant="hover_lift"
                onClick={() => toast.info(`Ver ${stat.label}`)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-zinc-600 text-sm">{stat.label}</p>
                    <p className="text-2xl font-semibold mt-1">{stat.value}</p>
                  </div>
                  <span className="text-3xl">{stat.icon}</span>
                </div>
              </CardEnhanced>
            ))}
          </div>
        )}

        {/* Task List */}
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Tareas Recientes</h2>
          {isLoading ? (
            <SkeletonTable rows={5} columns={3} />
          ) : (
            <div className="space-y-2">
              {tasks?.slice(0, 5).map((task) => (
                <CardEnhanced
                  key={task.id}
                  variant="interactive"
                  onClick={() => {
                    toast.info(`Abriendo: ${task.titulo}`);
                  }}
                  glowOnHover
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium">{task.titulo}</p>
                      <p className="text-sm text-zinc-500">{task.asignatura}</p>
                    </div>
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      {task.estado}
                    </span>
                  </div>
                </CardEnhanced>
              ))}
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}

// ============================================================================
// EJEMPLO 2: Card Grid con Hover Mejorado
// ============================================================================

export function AnimatedCardGridExample() {
  const toast = useToast();
  const mockCards = [
    { id: 1, title: 'Matemáticas', icon: '📐' },
    { id: 2, title: 'Lenguaje', icon: '📚' },
    { id: 3, title: 'Ciencias', icon: '🔬' },
    { id: 4, title: 'Historia', icon: '📜' },
    { id: 5, title: 'Educación Física', icon: '⚽' },
    { id: 6, title: 'Artes', icon: '🎨' },
  ];

  const handleCardClick = (title) => {
    toast.success(`✨ Entraste a ${title}`);
  };

  return (
    <PageTransition>
      <div className="p-6">
        <h1 className="text-3xl font-semibold mb-6">Mis Clases</h1>

        <div className="grid grid-cols-3 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockCards.map((card) => (
            <CardEnhanced
              key={card.id}
              variant="interactive"
              onClick={() => handleCardClick(card.title)}
              glowOnHover
              className="cursor-pointer"
            >
              <div className="text-center space-y-3">
                <div className="text-4xl">{card.icon}</div>
                <h3 className="font-semibold text-zinc-900">{card.title}</h3>
                <p className="text-xs text-zinc-500">Haz clic para ver detalles</p>
              </div>
            </CardEnhanced>
          ))}
        </div>
      </div>
    </PageTransition>
  );
}

// ============================================================================
// EJEMPLO 3: Tabla con Skeleton Loading
// ============================================================================

export function AnimatedTableExample() {
  const [isLoading, setIsLoading] = React.useState(true);
  const [students, setStudents] = React.useState([]);

  React.useEffect(() => {
    // Simular carga
    const timeout = setTimeout(() => {
      setStudents([
        { id: 1, name: 'Juan Pérez', email: 'juan@school.com', grade: '7.5' },
        { id: 2, name: 'María García', email: 'maria@school.com', grade: '8.2' },
        { id: 3, name: 'Carlos López', email: 'carlos@school.com', grade: '6.8' },
        { id: 4, name: 'Ana Martínez', email: 'ana@school.com', grade: '9.0' },
        { id: 5, name: 'Luis Fernández', email: 'luis@school.com', grade: '7.3' },
      ]);
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(timeout);
  }, []);

  return (
    <PageTransition>
      <div className="p-6">
        <h1 className="text-3xl font-semibold mb-6">Estudiantes</h1>

        {isLoading ? (
          <SkeletonTable rows={5} columns={4} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-zinc-900">
                    Nombre
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-zinc-900">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-zinc-900">
                    Calificación
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-zinc-900">
                    Acción
                  </th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id} className="border-b border-zinc-200 hover:bg-zinc-50">
                    <td className="px-4 py-3 text-sm text-zinc-900">{student.name}</td>
                    <td className="px-4 py-3 text-sm text-zinc-500">{student.email}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-zinc-900">
                      {student.grade}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                        Ver
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PageTransition>
  );
}

// ============================================================================
// EJEMPLO 4: Profile Card con Avatar Skeleton
// ============================================================================

export function AnimatedProfileExample() {
  const [isLoading, setIsLoading] = React.useState(true);
  const [profile, setProfile] = React.useState(null);

  React.useEffect(() => {
    const timeout = setTimeout(() => {
      setProfile({
        name: 'Juan Pérez García',
        role: 'Estudiante de 3° Medio',
        email: 'juan@school.com',
        bio: 'Apasionado por la programación y las matemáticas',
      });
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(timeout);
  }, []);

  return (
    <PageTransition>
      <div className="p-6 max-w-md mx-auto">
        <h1 className="text-3xl font-semibold mb-6">Mi Perfil</h1>

        {isLoading ? (
          <SkeletonPresets.profileCard />
        ) : (
          <CardEnhanced variant="hover_lift">
            <div className="space-y-4">
              {/* Avatar */}
              <div className="flex items-center gap-4">
                <div className="size-16 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center text-white text-2xl font-bold">
                  {profile.name.charAt(0)}
                </div>
                <div>
                  <h2 className="font-semibold text-lg">{profile.name}</h2>
                  <p className="text-sm text-zinc-500">{profile.role}</p>
                </div>
              </div>

              <hr className="border-zinc-200" />

              {/* Info */}
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-wide">Email</p>
                  <p className="text-sm font-medium text-zinc-900">{profile.email}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-wide">Biografía</p>
                  <p className="text-sm text-zinc-700">{profile.bio}</p>
                </div>
              </div>

              <button className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
                Editar Perfil
              </button>
            </div>
          </CardEnhanced>
        )}
      </div>
    </PageTransition>
  );
}

// ============================================================================
// EJEMPLO 5: Toast Notifications
// ============================================================================

export function AnimatedToastExample() {
  const toast = useToast();

  const handleSuccess = () => {
    toast.success('✨ Guardado correctamente');
  };

  const handleError = () => {
    toast.error('❌ Ocurrió un error');
  };

  const handleInfo = () => {
    toast.info('ℹ️ Información importante');
  };

  const handleWarning = () => {
    toast.warning('⚠️ Advertencia');
  };

  return (
    <PageTransition>
      <div className="p-6 max-w-md mx-auto">
        <h1 className="text-3xl font-semibold mb-6">Notificaciones</h1>

        <CardEnhanced variant="default">
          <div className="space-y-3">
            <p className="text-sm text-zinc-600 mb-4">
              Haz clic en un botón para ver la animación (esquina inferior derecha)
            </p>

            <button
              onClick={handleSuccess}
              className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
            >
              Success Toast
            </button>

            <button
              onClick={handleError}
              className="w-full bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
            >
              Error Toast
            </button>

            <button
              onClick={handleInfo}
              className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              Info Toast
            </button>

            <button
              onClick={handleWarning}
              className="w-full bg-yellow-600 text-white py-2 rounded-lg hover:bg-yellow-700 transition-colors text-sm font-medium"
            >
              Warning Toast
            </button>
          </div>
        </CardEnhanced>

        <p className="text-xs text-zinc-500 mt-4 text-center">
          Las notificaciones se cierran automáticamente después de 4 segundos
        </p>
      </div>
    </PageTransition>
  );
}

// ============================================================================
// EJEMPLO 6: Skeleton Variants
// ============================================================================

export function SkeletonVariantsExample() {
  const [showSkeleton, setShowSkeleton] = React.useState(true);

  return (
    <PageTransition>
      <div className="p-6 space-y-8">
        <div>
          <h1 className="text-3xl font-semibold mb-2">Skeleton Variants</h1>
          <button
            onClick={() => setShowSkeleton(!showSkeleton)}
            className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            {showSkeleton ? 'Mostrar Contenido' : 'Mostrar Skeleton'}
          </button>
        </div>

        {/* Card Skeleton */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Card Skeleton</h2>
          {showSkeleton ? <SkeletonCard /> : <CardEnhanced variant="hover_lift"><p>Card Content</p></CardEnhanced>}
        </div>

        {/* Grid Skeleton */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Grid Skeleton (4 items)</h2>
          {showSkeleton ? <SkeletonGrid count={4} columns="grid-cols-4" /> : <p>Grid Content</p>}
        </div>

        {/* Text Skeleton */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Text Skeleton (3 lines)</h2>
          {showSkeleton ? <SkeletonText lines={3} /> : <p>Lorem ipsum dolor sit amet…</p>}
        </div>

        {/* Avatar Skeleton */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Avatar Skeleton</h2>
          {showSkeleton ? <SkeletonAvatar size="size-20" /> : <div className="size-20 rounded-full bg-blue-400" />}
        </div>
      </div>
    </PageTransition>
  );
}

export default {
  AnimatedDashboardExample,
  AnimatedCardGridExample,
  AnimatedTableExample,
  AnimatedProfileExample,
  AnimatedToastExample,
  SkeletonVariantsExample,
};
